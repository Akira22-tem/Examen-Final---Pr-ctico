from flask import Flask, render_template, request, redirect, url_for, flash
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import re
from collections import Counter
from wordcloud import WordCloud
import emoji
import os
import base64
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'fighting_spirit_secret_key'

def limpiar_mensaje(texto):
    texto = re.sub(r'\d+', '', texto)
    texto = re.sub(r'http\S+', '', texto)
    texto = re.sub(r'[^\w\s]', '', texto)
    texto = texto.lower()
    return texto

def extraer_emojis(texto):
    try:
        return [c for c in texto if emoji.is_emoji(c)]
    except:
        return []

def procesar_chat(archivo_path):
    try:
        content = None
        for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
            try:
                with open(archivo_path, 'r', encoding=encoding) as file:
                    content = file.read()
                print(f"Archivo leído exitosamente con codificación: {encoding}")
                break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            raise Exception("No se pudo leer el archivo con ninguna codificación")
        
        lines = content.split('\n')
        print(f"Total de líneas en el archivo: {len(lines)}")
        
        patterns = [
            r'(\d{1,2}/\d{1,2}/\d{2,4}), (\d{1,2}:\d{2}) - (.*?): (.*)',
            r'(\d{1,2}/\d{1,2}/\d{4}), (\d{1,2}:\d{2}) - (.*?): (.*)',
            r'\[(\d{1,2}/\d{1,2}/\d{2,4}), (\d{1,2}:\d{2}:\d{2})\] (.*?): (.*)',
            r'(\d{1,2}/\d{1,2}/\d{2,4}) (\d{1,2}:\d{2}) - (.*?): (.*)'
        ]
        
        data = []
        matched_lines = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    groups = match.groups()
                    if len(groups) == 4:
                        date, time, sender, message = groups
                        data.append([date, time, sender, message])
                        matched_lines += 1
                        break
        
        print(f"Líneas procesadas exitosamente: {matched_lines}")
        
        if len(data) == 0:
            raise Exception("No se encontraron mensajes válidos en el formato esperado")
        
        df = pd.DataFrame(data, columns=['Fecha', 'Hora', 'Remitente', 'Mensaje'])
        print(f"DataFrame creado con {len(df)} filas")
        
        df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
        df['Hora'] = pd.to_datetime(df['Hora'], format='%H:%M', errors='coerce').dt.time
        df = df.dropna(subset=['Fecha'])
        
        df['Dia_semana'] = df['Fecha'].dt.day_name()
        df['Hora_int'] = df['Hora'].apply(lambda x: x.hour if x else 0)
        df['Año'] = df['Fecha'].dt.year
        df['Mes'] = df['Fecha'].dt.month_name()
        df['Mensaje_Limpio'] = df['Mensaje'].apply(limpiar_mensaje)
        df['Emojis'] = df['Mensaje'].apply(extraer_emojis)
        df['Cantidad_letras'] = df['Mensaje'].apply(len)
        df['Cantidad_palabras'] = df['Mensaje'].apply(lambda x: len(x.split()))
        df['Es_multimedia'] = df['Mensaje'].apply(lambda x: 1 if '<Media omitted>' in x or 'multimedia omitido' in x.lower() else 0)
        
        print(f"Procesamiento completado. DataFrame final: {len(df)} mensajes")
        return df
    
    except Exception as e:
        print(f"Error procesando chat: {e}")
        return None

def generar_graficos(df):
    graficos = {}
    plt.style.use('dark_background')
    fighting_colors = ['#d32f2f', '#ff6b35', '#ffd700', '#20b2aa', '#ff4444', '#ffaa00', '#00ddcc']
    
    # 1. Mensajes por usuario
    plt.figure(figsize=(14,8), facecolor='#1a1a1a')
    ax = plt.gca()
    ax.set_facecolor('#2d2d2d')
    top_users = df['Remitente'].value_counts().head(10)
    bars = plt.bar(range(len(top_users)), top_users.values, 
                   color=[fighting_colors[i % len(fighting_colors)] for i in range(len(top_users))])
    
    for i, bar in enumerate(bars):
        bar.set_edgecolor('#ffd700')
        bar.set_linewidth(2)
    
    plt.title('🏆 RANKING DE LUCHADORES DEL CHAT', fontsize=16, color='#ffd700', weight='bold', pad=20)
    plt.xlabel('Luchadores', fontsize=12, color='#20b2aa')
    plt.ylabel('Mensajes de Combate', fontsize=12, color='#20b2aa')
    plt.xticks(range(len(top_users)), [name[:15] + '...' if len(name) > 15 else name for name in top_users.index], 
               rotation=45, ha='right', color='#ffffff')
    plt.yticks(color='#ffffff')
    plt.grid(True, alpha=0.3, color='#404040')
    plt.tight_layout()
    graficos['usuarios'] = plt_to_base64()
    
    # 2. Mensajes por día de la semana
    plt.figure(figsize=(12,7), facecolor='#1a1a1a')
    ax = plt.gca()
    ax.set_facecolor('#2d2d2d')
    order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_names_es = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    day_counts = df['Dia_semana'].value_counts().reindex(order)
    
    bars = plt.bar(day_names_es, day_counts.values, 
                   color=['#d32f2f', '#ff6b35', '#ffd700', '#20b2aa', '#ff4444', '#ffaa00', '#00ddcc'])
    
    for bar in bars:
        bar.set_edgecolor('#ffd700')
        bar.set_linewidth(2)
    
    plt.title('⚔️ DÍAS DE ENTRENAMIENTO SEMANAL', fontsize=16, color='#ffd700', weight='bold', pad=20)
    plt.xlabel('Días de la Semana', fontsize=12, color='#20b2aa')
    plt.ylabel('Rounds de Conversación', fontsize=12, color='#20b2aa')
    plt.xticks(color='#ffffff')
    plt.yticks(color='#ffffff')
    plt.grid(True, alpha=0.3, color='#404040')
    plt.tight_layout()
    graficos['dias'] = plt_to_base64()
    
    # 3. Mensajes por hora del día
    plt.figure(figsize=(14,7), facecolor='#1a1a1a')
    ax = plt.gca()
    ax.set_facecolor('#2d2d2d')
    hour_counts = df['Hora_int'].value_counts().sort_index()
    
    colors = []
    for hour in hour_counts.index:
        if 6 <= hour <= 12:
            colors.append('#ffd700')
        elif 13 <= hour <= 18:
            colors.append('#ff6b35')
        elif 19 <= hour <= 23:
            colors.append('#d32f2f')
        else:
            colors.append('#20b2aa')
    
    bars = plt.bar(hour_counts.index, hour_counts.values, color=colors)
    for bar in bars:
        bar.set_edgecolor('#ffd700')
        bar.set_linewidth(1)
    
    plt.title('🥊 HORARIOS DE COMBATE DIARIO', fontsize=16, color='#ffd700', weight='bold', pad=20)
    plt.xlabel('Hora del Día', fontsize=12, color='#20b2aa')
    plt.ylabel('Intensidad de Batalla', fontsize=12, color='#20b2aa')
    plt.xticks(color='#ffffff')
    plt.yticks(color='#ffffff')
    plt.grid(True, alpha=0.3, color='#404040')
    plt.tight_layout()
    graficos['horas'] = plt_to_base64()
    
    # 4. Top palabras más frecuentes
    palabras = ' '.join(df['Mensaje_Limpio']).split()
    contador_palabras = Counter(palabras)
    palabras_comunes = contador_palabras.most_common(15)
    
    if palabras_comunes:
        palabras, frecuencias = zip(*palabras_comunes)
        plt.figure(figsize=(12,10), facecolor='#1a1a1a')
        ax = plt.gca()
        ax.set_facecolor('#2d2d2d')
        
        colors = []
        for i in range(len(palabras)):
            if i < 5:
                colors.append('#d32f2f')
            elif i < 10:
                colors.append('#ff6b35')
            else:
                colors.append('#ffd700')
        
        bars = plt.barh(range(len(palabras)), frecuencias, color=colors)
        for bar in bars:
            bar.set_edgecolor('#20b2aa')
            bar.set_linewidth(1)
        
        plt.yticks(range(len(palabras)), palabras, color='#ffffff')
        plt.title('💪 TÉCNICAS VERBALES MÁS PODEROSAS', fontsize=16, color='#ffd700', weight='bold', pad=20)
        plt.xlabel('Poder de Impacto', fontsize=12, color='#20b2aa')
        plt.xticks(color='#ffffff')
        plt.gca().invert_yaxis()
        plt.grid(True, alpha=0.3, color='#404040', axis='x')
        plt.tight_layout()
        graficos['palabras'] = plt_to_base64()
    
    # 5. Nube de palabras
    texto_completo = ' '.join(df['Mensaje_Limpio'])
    if texto_completo.strip():
        plt.figure(figsize=(16,10), facecolor='#1a1a1a')
        wordcloud = WordCloud(
            width=1200, height=600,
            background_color='#1a1a1a',
            colormap='autumn',
            max_words=100,
            relative_scaling=0.5,
            random_state=42
        ).generate(texto_completo)
        
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.title('🌪️ ESPÍRITU DEL GRUPO', fontsize=18, color='#ffd700', weight='bold', pad=30)
        plt.tight_layout()
        graficos['wordcloud'] = plt_to_base64()
    
    # 6. Top emojis
    todos_emojis = sum(df['Emojis'], [])
    if todos_emojis:
        contador_emojis = Counter(todos_emojis)
        emojis_comunes = contador_emojis.most_common(10)
        
        emojis, cuentas = zip(*emojis_comunes)
        plt.figure(figsize=(12,8), facecolor='#1a1a1a')
        ax = plt.gca()
        ax.set_facecolor('#2d2d2d')
        
        emoji_colors = ['#d32f2f', '#ff6b35', '#ffd700', '#20b2aa'] * 3
        bars = plt.barh(range(len(emojis)), cuentas, color=emoji_colors[:len(emojis)])
        
        for bar in bars:
            bar.set_edgecolor('#ffd700')
            bar.set_linewidth(2)
        
        plt.yticks(range(len(emojis)), emojis, fontsize=20, color='#ffffff')
        plt.title('😤 EXPRESIONES DE VICTORIA', fontsize=16, color='#ffd700', weight='bold', pad=20)
        plt.xlabel('Frecuencia de Uso', fontsize=12, color='#20b2aa')
        plt.xticks(color='#ffffff')
        plt.gca().invert_yaxis()
        plt.grid(True, alpha=0.3, color='#404040', axis='x')
        plt.tight_layout()
        graficos['emojis'] = plt_to_base64()
    
    # 7. Línea de tiempo
    plt.figure(figsize=(16,8), facecolor='#1a1a1a')
    ax = plt.gca()
    ax.set_facecolor('#2d2d2d')
    
    timeline_data = df.groupby('Fecha').size()
    plt.plot(timeline_data.index, timeline_data.values, 
             color='#d32f2f', linewidth=3, alpha=0.8)
    plt.fill_between(timeline_data.index, timeline_data.values, 
                     alpha=0.3, color='#ff6b35')
    
    plt.title('⚡ EVOLUCIÓN DEL ESPÍRITU DE LUCHA', fontsize=16, color='#ffd700', weight='bold', pad=20)
    plt.xlabel('Período de Entrenamiento', fontsize=12, color='#20b2aa')
    plt.ylabel('Intensidad Diaria', fontsize=12, color='#20b2aa')
    plt.xticks(color='#ffffff')
    plt.yticks(color='#ffffff')
    plt.grid(True, alpha=0.3, color='#404040')
    
    promedio = timeline_data.mean()
    plt.axhline(y=promedio, color='#ffd700', linestyle='--', alpha=0.7, linewidth=2)
    plt.text(timeline_data.index[len(timeline_data)//2], promedio + timeline_data.max()*0.05, 
             f'Nivel Base: {int(promedio)}', color='#ffd700', fontweight='bold')
    
    plt.tight_layout()
    graficos['timeline'] = plt_to_base64()
    
    return graficos

def plt_to_base64():
    img = BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight', dpi=100, facecolor='#1a1a1a')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode()
    plt.close()
    return plot_url

def generar_estadisticas(df):
    stats = {}
    stats['total_mensajes'] = len(df)
    stats['total_usuarios'] = df['Remitente'].nunique()
    stats['periodo'] = f"{df['Fecha'].min().strftime('%d/%m/%Y')} - {df['Fecha'].max().strftime('%d/%m/%Y')}"
    
    top_usuario = df['Remitente'].value_counts().iloc[0]
    stats['usuario_activo'] = df['Remitente'].value_counts().index[0]
    stats['mensajes_usuario_activo'] = top_usuario
    
    dia_activo = df.groupby('Fecha').size().idxmax()
    stats['dia_activo'] = dia_activo.strftime('%d/%m/%Y')
    stats['mensajes_dia_activo'] = df.groupby('Fecha').size().max()
    
    stats['hora_activa'] = df['Hora_int'].value_counts().index[0]
    
    todos_emojis = sum(df['Emojis'], [])
    stats['total_emojis'] = len(todos_emojis)
    
    stats['promedio_palabras'] = round(df['Cantidad_palabras'].mean(), 1)
    
    return stats

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No se seleccionó ningún archivo')
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        flash('No se seleccionó ningún archivo')
        return redirect(request.url)
    
    if file and file.filename.endswith('.txt'):
        filename = 'chat_temp.txt'
        file.save(filename)
        
        df = procesar_chat(filename)
        
        if df is not None and len(df) > 0:
            graficos = generar_graficos(df)
            estadisticas = generar_estadisticas(df)
            
            os.remove(filename)
            
            return render_template('resultados.html', 
                                 graficos=graficos, 
                                 estadisticas=estadisticas,
                                 filename=file.filename)
        else:
            flash('Error al procesar el archivo. Verifica que sea un chat de WhatsApp válido.')
            if os.path.exists(filename):
                os.remove(filename)
            return redirect(url_for('index'))
    
    flash('Por favor sube un archivo .txt')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)