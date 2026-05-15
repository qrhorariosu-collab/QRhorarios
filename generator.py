import pandas as pd
import qrcode
import re
from pathlib import Path
from datetime import datetime, time
import html
import os
import hashlib

def generar_hash_sala(nombre_sala):
    """Genera un hash corto para ofuscar la URL de la sala"""
    return hashlib.md5(nombre_sala.encode()).hexdigest()[:8]

def obtener_bloques_ocupados(hora_inicio, hora_fin):
    """Determina TODOS los bloques de 90 minutos que ocupa una clase"""
    bloques = [
        ("08:10:00", "09:40:00", "08:10-09:40"),
        ("09:50:00", "11:20:00", "09:50-11:20"),
        ("11:30:00", "13:00:00", "11:30-13:00"),
        ("14:10:00", "15:40:00", "14:10-15:40"),
        ("15:50:00", "17:20:00", "15:50-17:20"),
        ("17:30:00", "19:00:00", "17:30-19:00"),
        ("19:10:00", "20:40:00", "19:10-20:40"),
    ]
    
    hora_inicio_str = hora_inicio.strftime('%H:%M:%S') if isinstance(hora_inicio, time) else str(hora_inicio)
    hora_fin_str = hora_fin.strftime('%H:%M:%S') if isinstance(hora_fin, time) else str(hora_fin)
    
    bloques_ocupados = []
    
    for bloque_inicio, bloque_fin, bloque_label in bloques:
        if hora_inicio_str < bloque_fin and hora_fin_str > bloque_inicio:
            bloques_ocupados.append((bloque_inicio, bloque_fin, bloque_label))
    
    return bloques_ocupados

def leer_excel_semanas(archivo_excel, semana_actual="S11"):
    """Lee el Excel con formato de tabla plana"""
    print(f"📖 Leyendo archivo: {archivo_excel}")
    df = pd.read_excel(archivo_excel)
    
    if semana_actual in df.columns:
        df_activo = df[df[semana_actual] == 1].copy()
        print(f"✅ Filtrado por {semana_actual}: {len(df_activo)} registros activos")
    else:
        print(f"⚠️ No se encuentra {semana_actual}, usando todos")
        df_activo = df.copy()
    
    salas = {}
    
    for sala in df_activo['SALA'].unique():
        if pd.isna(sala):
            continue
        
        df_sala = df_activo[df_activo['SALA'] == sala]
        print(f"  📌 Procesando sala: {sala} ({len(df_sala)} clases)")
        
        horarios = {}
        
        for _, row in df_sala.iterrows():
            hora_inicio = row['HORA INICIO']
            hora_fin = row['HORA FIN']
            dia = row['DIA']
            asignatura = row['ASIGNATURA']
            nombre = row['NOMBRE']
            
            bloques_ocupados = obtener_bloques_ocupados(hora_inicio, hora_fin)
            
            for bloque_inicio, bloque_fin, bloque_label in bloques_ocupados:
                clave_bloque = f"{bloque_inicio}_{bloque_fin}"
                
                if clave_bloque not in horarios:
                    horarios[clave_bloque] = {
                        'hora': bloque_label,
                        'orden': int(bloque_inicio[:2]),
                        'clases': {}
                    }
                
                if dia not in horarios[clave_bloque]['clases']:
                    horarios[clave_bloque]['clases'][dia] = {
                        'codigo': asignatura,
                        'nombre': nombre,
                        'hora_inicio': hora_inicio.strftime('%H:%M') if isinstance(hora_inicio, time) else str(hora_inicio)[:5],
                        'hora_fin': hora_fin.strftime('%H:%M') if isinstance(hora_fin, time) else str(hora_fin)[:5],
                        'multibloque': len(bloques_ocupados) > 1
                    }
        
        if horarios:
            salas[sala] = horarios
    
    return salas

def generar_html_sala(nombre_sala, horarios, output_path, semana_actual):
    """Genera la página HTML para una sala (SIN enlaces a otras salas)"""
    
    dias_orden = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
    bloques_ordenados = sorted(horarios.values(), key=lambda x: x['orden'])
    
    html_tabla = '<div style="overflow-x: auto;"><table class="horario-table">\n'
    html_tabla += '<thead><tr><th>Horario</th>'
    for dia in dias_orden:
        html_tabla += f'<th>{dia}</th>'
    html_tabla += '</thead><tbody>\n'
    
    for bloque in bloques_ordenados:
        html_tabla += f'<tr><td class="hora-cell">{bloque["hora"]}</td>\n'
        
        for dia in dias_orden:
            if dia in bloque['clases']:
                clase = bloque['clases'][dia]
                
                if clase['codigo'] == 'BLOQUEO' or clase['nombre'] == 'BLOQUEO':
                    html_tabla += '<td class="bloqueo-cell">🔒 BLOQUEO</td>\n'
                else:
                    nombre_corto = clase['nombre'][:35] + '...' if len(clase['nombre']) > 35 else clase['nombre']
                    multibloque = clase.get('multibloque', False)
                    horario_extendido = f" ({clase['hora_inicio']}-{clase['hora_fin']})" if multibloque else ""
                    
                    html_tabla += f'''
                    <td class="clase-cell{' multibloque' if multibloque else ''}">
                        <div class="codigo">{html.escape(clase['codigo'])}</div>
                        <div class="nombre">{html.escape(nombre_corto)}<span class="horario-ext">{horario_extendido}</span></div>
                    </td>
                    '''
            else:
                html_tabla += '<td class="vacio-cell">—</td>\n'
        html_tabla += '</tr>\n'
    
    html_tabla += '</tbody></table></div>'
    
    # Limpiar nombre para mostrar (quitar prefijos)
    nombre_mostrar = nombre_sala.replace('PDSALA', 'SALA ')
    
    html_completo = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Horario - {html.escape(nombre_mostrar)}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 20px 40px rgba(0,0,0,0.2);
        }}
        .header {{
            background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
            color: white;
            padding: 25px;
            text-align: center;
        }}
        .header h1 {{ font-size: 1.8rem; margin-bottom: 5px; }}
        .semana-badge {{
            display: inline-block;
            background: #e74c3c;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.8rem;
            margin-top: 10px;
        }}
        .horario-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
        }}
        .horario-table th {{
            background: #34495e;
            color: white;
            padding: 12px;
        }}
        .horario-table td {{
            border: 1px solid #ddd;
            padding: 10px;
            vertical-align: top;
        }}
        .hora-cell {{
            background: #ecf0f1;
            font-weight: bold;
            text-align: center;
            width: 100px;
        }}
        .clase-cell {{ background: #fafafa; }}
        .clase-cell.multibloque {{ background: #e8f4fd; border-left: 3px solid #3498db; }}
        .codigo {{ font-weight: bold; color: #e74c3c; font-size: 0.8rem; }}
        .nombre {{ font-weight: 500; color: #2c3e50; margin-top: 5px; font-size: 0.8rem; }}
        .horario-ext {{ font-size: 0.7rem; color: #e67e22; margin-left: 5px; }}
        .bloqueo-cell {{ background: #fff3cd; color: #856404; text-align: center; font-weight: bold; }}
        .vacio-cell {{ background: #f9f9f9; color: #ccc; text-align: center; }}
        .footer {{
            background: #ecf0f1;
            padding: 15px;
            text-align: center;
            font-size: 0.75rem;
            color: #7f8c8d;
        }}
        .info-print {{
            text-align: center;
            margin-top: 20px;
            padding: 10px;
            background: #e8f4fd;
            border-radius: 10px;
            font-size: 0.8rem;
            color: #2c3e50;
        }}
        @media (max-width: 768px) {{
            .horario-table th, .horario-table td {{ padding: 6px; font-size: 0.7rem; }}
            .header h1 {{ font-size: 1.2rem; }}
        }}
        @media print {{
            body {{ background: white; padding: 0; }}
            .header {{ background: #2c3e50; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
            .info-print {{ display: none; }}
        }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>📋 {html.escape(nombre_mostrar)}</h1>
        <p>Horario semanal actualizado</p>
        <div class="semana-badge">📅 {semana_actual}</div>
    </div>
    {html_tabla}
    <div class="info-print">
        🔲 Escanea el código QR pegado en la puerta de esta sala para acceder siempre al horario actualizado
    </div>
    <div class="footer">
        🗓️ Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')}
    </div>
</div>
</body>
</html>'''
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_completo)

def generar_index_con_estilo(salas, semana_actual, output_dir):
    """Genera una página principal con buscador y mapeo de hashes"""
    
    # Crear un diccionario de mapeo: hash -> nombre_real
    mapeo_salas = {}
    for nombre_sala in salas.keys():
        hash_sala = generar_hash_sala(nombre_sala)
        mapeo_salas[hash_sala] = nombre_sala
    
    # Guardar el mapeo para referencia (opcional, no se publica)
    # Esto permite regenerar sin perder la relación
    
    index_html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Horarios - Sistema de Salas</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        
        .header {{
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }}
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
        }}
        .semana-badge {{
            background: #e74c3c;
            display: inline-block;
            padding: 8px 20px;
            border-radius: 30px;
            font-size: 1rem;
            margin-top: 10px;
        }}
        
        .buscador {{
            margin-bottom: 30px;
        }}
        .buscador input {{
            width: 100%;
            max-width: 500px;
            display: block;
            margin: 0 auto;
            padding: 15px 20px;
            font-size: 1rem;
            border: none;
            border-radius: 50px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            outline: none;
        }}
        
        .stats {{
            text-align: center;
            color: white;
            margin-bottom: 20px;
            font-size: 0.9rem;
        }}
        
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 25px;
        }}
        
        .card {{
            background: white;
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        .card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        }}
        .card-header {{
            background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
            color: white;
            padding: 15px;
            text-align: center;
        }}
        .card-header h3 {{
            font-size: 1.1rem;
        }}
        .card-qr {{
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
        }}
        .card-qr img {{
            width: 180px;
            height: 180px;
            margin: 0 auto;
            display: block;
        }}
        .card-buttons {{
            display: flex;
            gap: 10px;
            padding: 15px;
            background: #f8f9fa;
        }}
        .btn {{
            flex: 1;
            text-align: center;
            padding: 10px;
            border-radius: 10px;
            text-decoration: none;
            font-weight: bold;
            transition: all 0.3s;
            cursor: pointer;
            border: none;
            font-size: 0.85rem;
        }}
        .btn-ver {{
            background: #3498db;
            color: white;
        }}
        .btn-ver:hover {{
            background: #2980b9;
        }}
        .btn-descargar {{
            background: #27ae60;
            color: white;
        }}
        .btn-descargar:hover {{
            background: #229954;
        }}
        
        .footer {{
            text-align: center;
            color: white;
            margin-top: 40px;
            padding: 20px;
        }}
        
        .sin-resultados {{
            text-align: center;
            color: white;
            padding: 50px;
            font-size: 1.2rem;
        }}
        
        @media (max-width: 768px) {{
            .header h1 {{ font-size: 1.5rem; }}
            .grid {{ grid-template-columns: 1fr; }}
            .card-qr img {{ width: 140px; height: 140px; }}
        }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🏫 Sistema de Horarios por Sala</h1>
        <p>Selecciona una sala para ver su horario semanal</p>
        <div class="semana-badge">📅 Semana {semana_actual}</div>
    </div>
    
    <div class="buscador">
        <input type="text" id="buscador" placeholder="🔍 Buscar sala (ej: SALA 9, LABORATORIO, AUDITORIO...)" onkeyup="filtrarSalas()">
    </div>
    
    <div class="stats" id="stats">
        Mostrando <span id="mostrando">{len(salas)}</span> de {len(salas)} salas
    </div>
    
    <div class="grid" id="gridSalas">
'''
    
    for nombre_sala in salas.keys():
        hash_sala = generar_hash_sala(nombre_sala)
        nombre_mostrar = nombre_sala.replace('PDSALA', 'SALA ')
        
        index_html += f'''
        <div class="card" data-nombre="{html.escape(nombre_sala).lower()}">
            <div class="card-header">
                <h3>{html.escape(nombre_mostrar)}</h3>
            </div>
            <div class="card-qr">
                <img id="qr_{hash_sala}" src="qrs/{hash_sala}.png" alt="QR">
            </div>
            <div class="card-buttons">
                <a href="salas/{hash_sala}.html" class="btn btn-ver">📅 Ver Horario</a>
                <button class="btn btn-descargar" onclick="descargarQR('{hash_sala}', '{html.escape(nombre_mostrar)}')">📥 Descargar QR</button>
            </div>
        </div>
'''
    
    index_html += f'''
    </div>
    
    <div class="footer">
        <p>🔲 Los códigos QR son permanentes - Escanea una sola vez</p>
        <p>✅ Actualizado automáticamente desde Excel - Semana {semana_actual}</p>
        <p>📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
    </div>
</div>

<script>
function filtrarSalas() {{
    let input = document.getElementById('buscador');
    let filter = input.value.toLowerCase();
    let cards = document.getElementsByClassName('card');
    let visible = 0;
    
    for (let i = 0; i < cards.length; i++) {{
        let nombre = cards[i].getAttribute('data-nombre');
        if (nombre.includes(filter)) {{
            cards[i].style.display = "";
            visible++;
        }} else {{
            cards[i].style.display = "none";
        }}
    }}
    
    document.getElementById('mostrando').innerText = visible;
}}

function descargarQR(hash, nombreSala) {{
    let img = document.getElementById('qr_' + hash);
    let link = document.createElement('a');
    link.href = img.src;
    link.download = 'QR_' + nombreSala.replace(/ /g, '_') + '.png';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}}
</script>
</body>
</html>'''
    
    with open(output_dir / 'index.html', 'w', encoding='utf-8') as f:
        f.write(index_html)
    
    return mapeo_salas

def main():
    print("=" * 60)
    print("📖 GENERADOR DE HORARIOS - URLs OFUSCADAS")
    print("=" * 60)
    
    ARCHIVO_EXCEL = 'horarios.xlsx'
    SEMANA_ACTUAL = 'S10'
    
    if not os.path.exists(ARCHIVO_EXCEL):
        print(f"❌ Error: No se encuentra {ARCHIVO_EXCEL}")
        return
    
    salas = leer_excel_semanas(ARCHIVO_EXCEL, SEMANA_ACTUAL)
    
    if not salas:
        print("❌ No se encontraron salas con horarios")
        return
    
    print(f"\n✅ Encontradas {len(salas)} salas")
    
    output_dir = Path('output')
    salas_dir = output_dir / 'salas'
    qrs_dir = output_dir / 'qrs'
    
    salas_dir.mkdir(parents=True, exist_ok=True)
    qrs_dir.mkdir(parents=True, exist_ok=True)
    
    # Diccionario para guardar mapeo (útil para debugging)
    mapeo = {}
    
    # Generar página de cada sala usando hash
    for nombre_sala, horarios in salas.items():
        hash_sala = generar_hash_sala(nombre_sala)
        mapeo[hash_sala] = nombre_sala
        print(f"📝 {nombre_sala} → {hash_sala}.html")
        
        generar_html_sala(nombre_sala, horarios, salas_dir / f'{hash_sala}.html', SEMANA_ACTUAL)
        
        # Generar QR con URL ofuscada
        url = f"https://qrhorariosu-collab.github.io/QRhorarios/salas/{hash_sala}.html"
        qr = qrcode.QRCode(box_size=10, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(qrs_dir / f'{hash_sala}.png')
    
    # Guardar mapeo (archivo oculto, no visible desde la web)
    with open(output_dir / '.mapeo.json', 'w', encoding='utf-8') as f:
        import json
        json.dump(mapeo, f, indent=2, ensure_ascii=False)
    
    # Generar index
    generar_index_con_estilo(salas, SEMANA_ACTUAL, output_dir)
    
    print("\n" + "=" * 60)
    print("✅ ¡GENERACIÓN COMPLETADA!")
    print(f"📊 {len(salas)} salas procesadas")
    print(f"🌐 https://qrhorariosu-collab.github.io/QRhorarios/")
    print("🔒 URLs ofuscadas con hash MD5 (8 caracteres)")
    print("=" * 60)

if __name__ == "__main__":
    main()