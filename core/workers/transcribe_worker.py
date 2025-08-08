# core/workers/transcribe_worker.py
import os
import time
import re
from PySide6.QtCore import QObject, Signal

import torch
import opencc

def format_time(seconds, separator='.'):
    """Converts seconds to HH:MM:SS,ms format, allowing custom separator for SRT."""
    ms = int((seconds - int(seconds)) * 1000)
    s = int(seconds)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}{separator}{ms:03d}"
    
def format_time_lrc(seconds):
    """Converts seconds to MM:SS.ms (2-digit) format for LRC."""
    ms = int((seconds - int(seconds)) * 100)
    s = int(seconds)
    m, s = divmod(s, 60)
    return f"{m:02d}:{s:02d}.{ms:02d}"

class TranscribeWorker(QObject):
    finished = Signal(bool, str)
    log_message = Signal(str)
    progress_update = Signal(int, str)

    def __init__(self, params):
        super().__init__()
        self.params = params
        self.whisper_result = None
        self.converter = opencc.OpenCC('t2s')

    # 【最终版】基于时间插值的、最可靠的字幕切分函数
    def _resegment_by_interpolation(self, result, max_chars=20, max_duration=5.0):
        """
        信任Whisper的原始分段时间戳，在内部按规则切分文本，并按比例估算新时间戳。
        这是解决音画同步问题的最可靠方法。
        """
        original_segments = result.get('segments', [])
        new_segments = []

        self.log_message.emit("ℹ️ 使用时间插值法进行字幕切分...")

        for segment in original_segments:
            full_text_raw = segment['text'].strip()
            full_text = self.converter.convert(full_text_raw)
            if not full_text:
                continue

            start_time = segment['start']
            end_time = segment['end']
            duration = end_time - start_time
            
            # 如果原始片段本身就符合要求，直接添加
            if len(full_text) <= max_chars and duration <= max_duration:
                segment['text'] = full_text # 确保文本是简体
                new_segments.append(segment)
                continue
            
            # 按标点符号进行初步切分
            sentences = re.split(r'(，|。|？|！|,|\.|\?|!)', full_text)
            
            chunks = []
            for i in range(0, len(sentences), 2):
                chunk = sentences[i]
                if i + 1 < len(sentences):
                    chunk += sentences[i+1]
                if chunk.strip():
                    chunks.append(chunk.strip())

            current_char_pos = 0
            for text_chunk in chunks:
                # 如果小片段依然太长，则强制按字数切分
                if len(text_chunk) > max_chars:
                    sub_chunks = [text_chunk[i:i+max_chars] for i in range(0, len(text_chunk), max_chars)]
                    for sub_chunk in sub_chunks:
                        start_char_index = current_char_pos
                        end_char_index = current_char_pos + len(sub_chunk)
                        
                        # 按比例计算时间戳
                        chunk_start = start_time + (start_char_index / len(full_text)) * duration if len(full_text) > 0 else start_time
                        chunk_end = start_time + (end_char_index / len(full_text)) * duration if len(full_text) > 0 else end_time
                        
                        new_segments.append({'start': chunk_start, 'end': chunk_end, 'text': sub_chunk})
                        current_char_pos += len(sub_chunk)
                else:
                    start_char_index = current_char_pos
                    end_char_index = current_char_pos + len(text_chunk)

                    chunk_start = start_time + (start_char_index / len(full_text)) * duration if len(full_text) > 0 else start_time
                    chunk_end = start_time + (end_char_index / len(full_text)) * duration if len(full_text) > 0 else end_time

                    new_segments.append({'start': chunk_start, 'end': chunk_end, 'text': text_chunk})
                    current_char_pos += len(text_chunk)

        return new_segments

    def run(self):
        try:
            import whisper

            media_file = self.params['media_file']
            model_name = self.params['model']
            language_choice = self.params['language']
            model_root = self.params['model_root']
            device_choice = self.params['device']
            
            self.log_message.emit(f"▶️ 任务开始：使用模型 '{model_name}'")
            
            # --- 设备选择逻辑 ---
            self.progress_update.emit(5, "检测计算设备...")
            device = "cpu"
            if device_choice == "自动 (优先GPU)" or device_choice == "GPU (CUDA)":
                if torch.cuda.is_available():
                    device = "cuda"
                    self.log_message.emit("✅ 检测到CUDA设备，将使用GPU进行计算。")
                else:
                    self.log_message.emit("⚠️ 未检测到可用的CUDA设备，将自动切换到CPU。")
                    if device_choice == "GPU (CUDA)":
                        self.log_message.emit("   (您选择了'GPU (CUDA)'，但环境不满足条件。)")
            else:
                 self.log_message.emit("ℹ️ 已选择使用CPU进行计算。")
            
            # --- 1. Model Loading ---
            self.progress_update.emit(10, f"正在加载模型: {model_name} (到 {device})...")
            self.log_message.emit(f"模型下载/加载目录: {model_root}")
            os.makedirs(model_root, exist_ok=True)
            model = whisper.load_model(model_name, download_root=model_root, device=device)
            self.log_message.emit("✅ 模型加载成功。")

            # --- 2. 设置转录参数 ---
            # 【修改】不再请求 word_timestamps，因为它不稳定且我们不再使用它
            transcribe_options = {
                "fp16": False,
                "verbose": True,
                "condition_on_previous_text": False
            }
            
            language_for_whisper = None
            if language_choice == 'zh-hans':
                language_for_whisper = 'zh'
            elif language_choice != 'auto':
                language_for_whisper = language_choice
            
            if language_for_whisper:
                transcribe_options['language'] = language_for_whisper

            simplified_chinese_prompt = "以下是普通话的简体字。"
            if language_choice == 'zh-hans' or language_choice == 'auto':
                transcribe_options['initial_prompt'] = simplified_chinese_prompt
                self.log_message.emit(f"ℹ️ 已启用简体中文优先模式。")

            # --- 3. Transcription ---
            self.progress_update.emit(25, "正在识别音频 (此过程无精确进度)...")
            self.log_message.emit("开始语音转文字，这可能需要很长时间，请耐心等待...")
            
            start_time = time.time()
            result = model.transcribe(media_file, **transcribe_options)
            end_time = time.time()
            
            self.whisper_result = result
            self.progress_update.emit(85, "识别完成！")
            self.log_message.emit(f"✅ 识别完成！耗时: {end_time - start_time:.2f} 秒。")
            detected_lang = result.get('language', 'unknown')
            self.log_message.emit(f"ℹ️ 检测到的语言: {detected_lang}")

            # --- 4. 调用最终版的切分函数 ---
            self.progress_update.emit(88, "正在进行简繁转换和字幕切分...")
            resegmented_segments = self._resegment_by_interpolation(self.whisper_result, max_chars=20, max_duration=5.0)
            self.whisper_result['segments'] = resegmented_segments
            self.log_message.emit("✅ 处理完成。")

            # --- 5. Exporting Files ---
            self.progress_update.emit(90, "正在导出文件...")
            self.export_files()
            
            self.finished.emit(True, "语音转文字任务成功完成！")

        except Exception as e:
            self.log_message.emit(f"❌ 发生严重错误: {str(e)}")
            import traceback
            self.log_message.emit(traceback.format_exc())
            self.finished.emit(False, f"任务失败: {e}")
            
    def export_files(self):
        base_path = os.path.join(self.params['output_dir'], self.params['output_filename'])
        
        for fmt in self.params['export_formats']:
            output_path = f"{base_path}.{fmt}"
            self.log_message.emit(f"正在写入: {output_path}")
            try:
                if fmt == 'txt': self._write_txt(output_path)
                elif fmt == 'vtt': self._write_vtt(output_path)
                elif fmt == 'srt': self._write_srt(output_path)
                elif fmt == 'lrc': self._write_lrc(output_path)
                self.log_message.emit("✅ 写入成功。")
            except Exception as e:
                self.log_message.emit(f"❌ 写入 {fmt} 文件失败: {e}")

    def _write_txt(self, path):
        with open(path, 'w', encoding='utf-8') as f:
            for segment in self.whisper_result['segments']:
                start, end, text = format_time(segment['start']), format_time(segment['end']), segment['text'].strip()
                f.write(f"[{start} --> {end}] {text}\n")
            
    def _write_vtt(self, path):
        with open(path, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")
            for segment in self.whisper_result['segments']:
                start, end, text = format_time(segment['start']), format_time(segment['end']), segment['text'].strip()
                f.write(f"{start} --> {end}\n{text}\n\n")

    def _write_srt(self, path):
        with open(path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(self.whisper_result['segments'], 1):
                start, end, text = format_time(segment['start'], separator=','), format_time(segment['end'], separator=','), segment['text'].strip()
                f.write(f"{i}\n{start} --> {end}\n{text}\n\n")

    def _write_lrc(self, path):
        with open(path, 'w', encoding='utf-8') as f:
            for segment in self.whisper_result['segments']:
                start, text = format_time_lrc(segment['start']), segment['text'].strip()
                f.write(f"[{start}]{text}\n")