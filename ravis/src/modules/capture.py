# ============================================
# MÓDULO DE CAPTURA DE TELA COM SELEÇÃO DE REGIÃO
# ============================================
# Propósito: Script standalone para captura de tela via seleção visual de região
#
# Funcionalidades:
#   - Janela fullscreen transparente para seleção
#   - Arrastar para selecionar área desejada
#   - Tecla ESC para cancelar
#   - Captura apenas região selecionada
#   - Salva em ui/assets/captures/ultima_captura.png
#
# Como usar:
#   python capture.py
#   (Abre janela transparente, usuário seleciona área)
#
# Saída (stdout):
#   - CAPTURA_OK:/caminho/da/imagem.png
#   - CAPTURA_CANCELADA
#   - CAPTURA_ERRO:mensagem
#
# Dependências:
#   - tkinter (biblioteca padrão Python)
#   - mss (captura de tela)
#   - Pillow (processamento de imagem)
# ============================================

import sys
import os

import tkinter as tk
from PIL import Image
import mss


# ============================================================
# Constantes
# ============================================================
CAPTURE_COLOR = '#00D4FF'
CAPTURE_WIDTH = 3
MIN_SELECTION_SIZE = 10


# ============================================================
# Função: create_selection_window()
# ============================================================
# Propósito: Cria janela fullscreen transparente para seleção
#
# Retorna:
#   - root: Instância Tk root
#   - canvas: Canvas para desenho da seleção
#   - label: Label de instrução
# ============================================================
def create_selection_window():
    """
    Cria a janela de seleção fullscreen com transparência.
    
    Returns:
        tuple: (root, canvas, label)
    """
    root = tk.Tk()
    root.attributes('-fullscreen', True)
    root.attributes('-alpha', 0.3)
    root.configure(bg='black')
    root.overrideredirect(True)
    root.attributes('-topmost', True)
    root.config(cursor="crosshair")
    
    root.update()
    root.lift()
    root.focus_force()
    
    canvas = tk.Canvas(root, bg='black', highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)
    
    label = tk.Label(
        root,
        text='Clique e arraste para selecionar uma regiao\nPressione ESC para cancelar',
        bg='black',
        fg='white',
        font=('Arial', 20, 'bold')
    )
    label.place(relx=0.5, rely=0.05, anchor=tk.CENTER)
    
    return root, canvas, label


# ============================================================
# Função: setup_selection_handlers()
# ============================================================
# Propósito: Configura handlers de eventos para seleção de região
#
# Args:
#   - canvas: Canvas tkinter para bind de eventos
#   - root: Instância Tk root para bind de teclado
#   - result: Dicionário para armazenar coordenadas
#   - rect: Referência ao retângulo de seleção
#
# Retorna:
#   - Função on_mouse_up configurada (para uso no bind)
# ============================================================
def setup_selection_handlers(canvas, root, result, rect):
    """
    Configura handlers de eventos do mouse e teclado.
    
    Args:
        canvas: Canvas para eventos de mouse
        root: Janela root para eventos de teclado
        result: Dicionário com coordenadas (x1, y1, x2, y2)
        rect: Referência ao retângulo (mutável via nonlocal)
    
    Returns:
        Função on_mouse_up configurada
    """
    def on_mouse_down(event):
        nonlocal rect
        result['x1'] = event.x_root
        result['y1'] = event.y_root
        rect = canvas.create_rectangle(
            event.x_root, event.y_root, event.x_root, event.y_root,
            outline=CAPTURE_COLOR,
            width=CAPTURE_WIDTH
        )
        return rect
    
    def on_mouse_drag(event):
        nonlocal rect
        if rect and result['x1'] is not None:
            canvas.coords(rect, result['x1'], result['y1'], event.x_root, event.y_root)
    
    def on_mouse_up(event):
        result['x2'] = event.x_root
        result['y2'] = event.y_root
        root.quit()
    
    def on_key_press(event):
        if event.keysym == 'Escape':
            result['x1'] = None
            root.quit()
    
    canvas.bind('<Button-1>', on_mouse_down)
    canvas.bind('<B1-Motion>', on_mouse_drag)
    canvas.bind('<ButtonRelease-1>', on_mouse_up)
    root.bind('<Key>', on_key_press)
    
    return on_mouse_up


# ============================================================
# Função: get_normalized_coordinates()
# ============================================================
# Propósito: Normaliza coordenadas para formato (x1, y1, x2, y2)
#
# Args:
#   - result: Dicionário com coordenadas
#
# Retorna:
#   - tuple: (x1, y1, width, height) normalizados
# ============================================================
def get_normalized_coordinates(result):
    """
    Normaliza coordenadas independente da direção do arrasto.
    
    Args:
        result: Dicionário com x1, y1, x2, y2
    
    Returns:
        tuple: (x1, y1, width, height) normalizados
    """
    x1 = min(result['x1'], result['x2'])
    y1 = min(result['y1'], result['y2'])
    x2 = max(result['x1'], result['x2'])
    y2 = max(result['y1'], result['y2'])
    
    width = x2 - x1
    height = y2 - y1
    
    return x1, y1, width, height


# ============================================================
# Função: capture_screen_region()
# ============================================================
# Propósito: Captura região específica da tela
#
# Args:
#   - x: Coordenada X inicial
#   - y: Coordenada Y inicial
#   - width: Largura da região
#   - height: Altura da região
#
# Retorna:
#   - PIL.Image ou None se erro
# ============================================================
def capture_screen_region(x, y, width, height):
    """
    Captura região específica da tela usando mss.
    
    Args:
        x: Coordenada X inicial
        y: Coordenada Y inicial
        width: Largura da região
        height: Altura da região
    
    Returns:
        PIL.Image ou None em caso de erro
    """
    try:
        with mss.mss() as sct:
            monitor = {
                "top": int(y),
                "left": int(x),
                "width": int(width),
                "height": int(height)
            }
            img = sct.grab(monitor)
            return Image.frombytes("RGB", img.size, img.rgb)
    except Exception as e:
        print(f"CAPTURA_ERRO:{e}")
        return None


# ============================================================
# Função: save_capture()
# ============================================================
# Propósito: Salva imagem capturada em arquivo
#
# Args:
#   - pil_image: Imagem PIL para salvar
#
# Retorna:
#   - str: Caminho do arquivo salvo ou None se erro
# ============================================================
def save_capture(pil_image):
    """
    Salva imagem capturada no diretório de capturas.
    
    Args:
        pil_image: Imagem PIL a ser salva
    
    Returns:
        str: Caminho do arquivo salvo ou None se erro
    """
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        captures_dir = os.path.join(project_root, "ui", "assets", "captures")
        os.makedirs(captures_dir, exist_ok=True)
        
        output_path = os.path.join(captures_dir, "ultima_captura.png")
        pil_image.save(output_path, "PNG")
        
        return output_path
    except Exception as e:
        print(f"CAPTURA_ERRO:{e}")
        return None


# ============================================================
# Função: main()
# ============================================================
# Propósito: Executa o fluxo completo de seleção e captura
#
# Fluxo:
#   1. Cria janela fullscreen transparente (tkinter)
#   2. Usuário arrasta para selecionar região
#   3. Captura região usando mss
#   4. Salva imagem usando Pillow
#
# Saída (stdout):
#   - CAPTURA_OK:/caminho/da/imagem.png
#   - CAPTURA_CANCELADA
#   - CAPTURA_ERRO:mensagem
# ============================================================
def main():
    """Executa a seleção de região e captura de tela."""
    print("[Capture] ===== INICIANDO SCRIPT DE CAPTURA =====", flush=True)
    
    result = {"x1": None, "y1": None, "x2": None, "y2": None}
    rect = None
    
    root, canvas, label = create_selection_window()
    setup_selection_handlers(canvas, root, result, rect)
    
    print("[Capture] Janela criada, iniciando mainloop...", flush=True)
    
    try:
        root.mainloop()
    finally:
        root.destroy()
    
    if result['x1'] is None:
        print("CAPTURA_CANCELADA", flush=True)
        sys.exit(0)
    
    x1, y1, width, height = get_normalized_coordinates(result)
    
    if width < MIN_SELECTION_SIZE or height < MIN_SELECTION_SIZE:
        print("CAPTURA_CANCELADA", flush=True)
        sys.exit(0)
    
    print(f"[Capture] Capturando regiao: x={x1}, y={y1}, w={width}, h={height}", flush=True)
    
    pil_image = capture_screen_region(x1, y1, width, height)
    
    if pil_image is None:
        sys.exit(1)
    
    output_path = save_capture(pil_image)
    
    if output_path:
        print(f"CAPTURA_OK:{output_path}", flush=True)
        sys.exit(0)
    else:
        sys.exit(1)


# ============================================================
# Ponto de entrada do script
# ============================================================
if __name__ == "__main__":
    main()
