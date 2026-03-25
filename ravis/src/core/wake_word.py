# ============================================
# MÓDULO DE DETECÇÃO DE PALAVRA DE ATIVAÇÃO (WAKE WORD)
# ============================================
# Propósito: Detectar palavra de ativação ("Ravis") via microfone
#
# Funcionalidades:
#   - Monitoramento contínuo de áudio do microfone
#   - Detecção por modelo Whisper
#   - Voice Activity Detection (VAD) por energia
#   - Cooldown entre ativações (debounce)
#   - Fallback GPU → CPU
#   - Threshold de confiança
#   - Múltiplas wake words suportadas
#   - Estatísticas de uso
#
# Uso:
#   def on_wake():
#       print("Ravis ativado!")
#   
#   wake = WakeWord(callback=on_wake)
#   wake.start()
# ============================================

import threading
import time
import numpy as np
from faster_whisper import WhisperModel
from src.config import (
    WAKE_WORD, WAKE_WORD_ALTERNATIVES, WAKE_WORD_MODEL,
    WAKE_WORD_AUDIO_DURATION, WAKE_WORD_VOICE_THRESHOLD,
    WAKE_WORD_ACTIVATION_COOLDOWN, WAKE_WORD_CONFIDENCE_THRESHOLD
)
import sounddevice as sd


# ============================================================
# Classe: WakeWord
# ============================================================
# Propósito: Detectar palavra de ativação em stream de áudio
#
# Atributos:
#   - callback: Função a ser chamada quando wake word for detectada
#   - running: Flag indicando se está ativo
#   - thread: Thread de monitoramento de áudio
#   - model: Modelo Whisper carregado
#   - last_activation: Timestamp da última ativação
#   - activation_count: Total de ativações
#   - total_listen_time: Tempo total de escuta
#   - last_audio: Último áudio processado
# ============================================================
class WakeWord:
    """
    Detector de palavra de ativação usando Whisper.
    
    Monitora continuamente o microfone e executa callback
    quando a wake word é detectada com confiança adequada.
    """
    
    def __init__(self, callback):
        """
        Inicializa o detector de wake word.
        
        Args:
            callback: Função a ser chamada quando detectada a wake word
        """
        self.callback = callback
        self.running = False
        self.thread = None
        self.model = None
        self.last_activation = 0
        self.activation_count = 0
        self.total_listen_time = 0
        self.last_audio = None
    
    
    # ============================================================
    # _check_audio_device()
    # ============================================================
    # Propósito: Verificar disponibilidade de microfone
    #
    # Retorna:
    #   - bool: True se microfone disponível
    # ============================================================
    def _check_audio_device(self) -> bool:
        """
        Verifica se há microfone disponível no sistema.
        
        Returns:
            bool: True se dispositivo de entrada disponível
        """
        try:
            devices = sd.query_devices()
            if devices is None or devices['max_input_channels'] < 1:
                print("[WAKE] Nenhum microfone encontrado")
                return False
            return True
        except Exception as e:
            print(f"[WAKE] Erro ao verificar dispositivo: {e}")
            return False
    
    
    # ============================================================
    # _is_speaking()
    # ============================================================
    # Propósito: Detectar presença de voz no áudio
    #
    # Args:
    #   - audio_data: Array numpy com dados de áudio
    #
    # Retorna:
    #   - bool: True se há voz detectada
    # ============================================================
    def _is_speaking(self, audio_data) -> bool:
        """
        Detecta se há voz no áudio usando threshold de energia.
        
        Args:
            audio_data: Array numpy com dados de áudio
        
        Returns:
            bool: True se energia > threshold (há voz)
        """
        try:
            energy = np.abs(audio_data).mean()
            return energy > WAKE_WORD_VOICE_THRESHOLD
        except:
            return True
    
    
    # ============================================================
    # _should_activate()
    # ============================================================
    # Propósito: Verificar se pode ativar (debounce)
    #
    # Retorna:
    #   - bool: True se cooldown expirou
    # ============================================================
    def _should_activate(self) -> bool:
        """
        Verifica se o cooldown entre ativações expirou.
        
        Returns:
            bool: True se pode ativar novamente
        """
        now = time.time()
        return (now - self.last_activation) > WAKE_WORD_ACTIVATION_COOLDOWN
    
    
    # ============================================================
    # _contains_wake_word()
    # ============================================================
    # Propósito: Verificar se texto contém wake word
    #
    # Args:
    #   - text: Texto transcrito do áudio
    #
    # Retorna:
    #   - bool: True se wake word detectada
    # ============================================================
    def _contains_wake_word(self, text: str) -> bool:
        """
        Verifica se o texto contém alguma das wake words configuradas.
        
        Args:
            text: Texto transcrito pelo Whisper
        
        Returns:
            bool: True se contém wake word
        """
        text_lower = text.lower()
        all_wake_words = [WAKE_WORD] + WAKE_WORD_ALTERNATIVES
        return any(wake_word in text_lower for wake_word in all_wake_words)
    
    
    # ============================================================
    # load_model()
    # ============================================================
    # Propósito: Carregar modelo Whisper
    #
    # Retorna:
    #   - bool: True se sucesso
    # ============================================================
    def load_model(self) -> bool:
        """
        Carrega o modelo Whisper para transcrição.
        
        Tenta GPU primeiro, faz fallback para CPU se necessário.
        
        Returns:
            bool: True se modelo carregado com sucesso
        """
        print("[WAKE] Carregando modelo Whisper...")
        
        for device in ["cuda", "cpu"]:
            try:
                self.model = WhisperModel(WAKE_WORD_MODEL, device=device, compute_type="int8")
                print(f"[WAKE] Modelo carregado ({device})")
                return True
            except Exception as e:
                print(f"[WAKE] Tentando {device}: {e}")
                continue
        
        print(f"[WAKE] Erro ao carregar modelo")
        return False
    
    
    # ============================================================
    # start()
    # ============================================================
    # Propósito: Iniciar monitoramento de microfone
    # ============================================================
    def start(self):
        """
        Inicia o monitoramento de microfone em thread separada.
        
        Verifica dispositivo de áudio e carrega modelo antes de iniciar.
        """
        if not self._check_audio_device():
            print("[WAKE] Dispositivo de áudio não disponível")
            return
        
        if not self.model:
            if not self.load_model():
                return
        
        self.running = True
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()
        print("[WAKE] Wake word iniciado")
    
    
    # ============================================================
    # stop()
    # ============================================================
    # Propósito: Parar monitoramento de microfone
    # ============================================================
    def stop(self):
        """
        Para o monitoramento de microfone e exibe estatísticas.
        """
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        print(f"[WAKE] Parado. Ativações: {self.activation_count}, Tempo total: {self.total_listen_time:.1f}s")
    
    
    # ============================================================
    # get_stats()
    # ============================================================
    # Propósito: Retornar estatísticas de uso
    #
    # Retorna:
    #   - dict: Estatísticas do detector
    # ============================================================
    def get_stats(self) -> dict:
        """
        Retorna estatísticas de uso do detector.
        
        Returns:
            dict: Contendo activation_count, total_listen_time e last_activation
        """
        return {
            "activation_count": self.activation_count,
            "total_listen_time": self.total_listen_time,
            "last_activation": self.last_activation
        }
    
    
    # ============================================================
    # _listen()
    # ============================================================
    # Propósito: Loop de escuta contínua
    # ============================================================
    def _listen(self):
        """
        Loop principal de escuta do microfone.
        
        Grava áudio, detecta voz, transcreve e verifica wake word.
        """
        print("[WAKE] Escutando...")
        start_time = time.time()
        
        while self.running:
            try:
                duration = int(16000 * WAKE_WORD_AUDIO_DURATION)
                audio_data = sd.rec(duration, samplerate=16000, channels=1, dtype=np.float32)
                sd.wait()
                
                self.total_listen_time += time.time() - start_time
                start_time = time.time()
                
                if not self._is_speaking(audio_data):
                    continue
                
                audio_int16 = (audio_data.flatten() * 32767).astype(np.int16)
                self.last_audio = audio_int16
                
                segments, _ = self.model.transcribe(
                    audio_int16,
                    language="pt",
                    beam_size=1
                )
                
                for segment in segments:
                    if segment.avg_logprob < WAKE_WORD_CONFIDENCE_THRESHOLD:
                        continue
                    
                    text = segment.text.lower().strip()
                    if text:
                        print(f"[WAKE] Detectado: {text}")
                        
                        if self._contains_wake_word(text):
                            if self._should_activate():
                                print("[WAKE] Wake word detectada!")
                                self.last_activation = time.time()
                                self.activation_count += 1
                                self.callback()
                            else:
                                print("[WAKE] Em cooldown, ignorando")
                            
            except Exception as e:
                print(f"[WAKE] Erro na escuta: {e}")
                time.sleep(1)
                continue
