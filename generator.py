import pandas as pd
import qrcode
import re
from pathlib import Path
from datetime import datetime
import html
import os

def leer_excel_semanas(archivo_excel, semana_actual="S10"):
    """Lee el Excel con formato de tabla plana"""
    print(f"📖 Leyendo archivo: {archivo_excel}")
    df = pd.read_excel(archivo_excel)
    
    # Filtrar por semana actual
    if semana_actual in df.columns:
        df_activo = df[df[semana_actual] == 1].copy()
        print(f"✅ Filtrado por {semana_actual}: {len(df_activo)} registros activos")
    else:
        print(f"⚠️ No se encuentra {semana_actual}, usando todos")
        df_activo = df.copy()
    
    # Agrupar por sala
    salas = {}
    
    for sala in df_activo['SALA'].unique():
        if pd.isna(sala):
            continue
        
        df_sala = df_activo[df_activo['SALA'] == sala]
        print(f"  📌 Procesando sala: {sala} ({len(df_sala)} clases)")
        
        # Crear estructura de horarios: por hora_inicio y día
        horarios = {}
        
        for _, row in df_sala.iterrows():
            hora_inicio = row['HORA INICIO']
            hora_fin = row['HORA FIN']
            dia = row['DIA']
            asignatura = row['ASIGNATURA']
            nombre = row['NOMBRE']
            
            # Solo procesar si no es BLOQUEO
            if asignatura == 'BLOQUEO' or nombre == 'BLOQUEO':
                continue
            
            # Usar hora_inicio como clave
            if hora_inicio not in horarios:
                horarios[hora_inicio] = {
                    'hora': f"{hora_inicio[:5]} - {hora_fin[:5]}",
                    'clases': {}
                }
            
            horarios[hora_inicio]['clases'][dia] = {
                'codigo': asignatura,
                'nombre': nombre
            }
        
        if horarios:
            salas[sala] = horarios
    
    return salas

def generar_html_sala(nombre_sala, horarios, output_path, semana_actual):
    """Genera la página HTML para una sala"""
    
    dias_orden = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
    
    # Ordenar horas
    horas_ordenadas = sorted(horarios.keys())
    
    # Construir tabla
    html_tabla = '<div style="overflow-x: auto;"><table class="horario-table">\n'
    html_tabla += '<thead><tr><th>Horario</th>'
    for dia in dias_orden:
        html_tabla += f'<th>{dia}</th>'
    html_tabla += '</thead><tbody>\n'
    
    for hora_key in horas_ordenadas:
        hora_info = horarios[hora_key]
        html_tabla += f'<tr><td class="hora-cell">{hora_info["hora"]}</td>\n'
        
        for dia in dias_orden:
            if dia in hora_info['clases']:
                clase = hora_info['clases'][dia]
                nombre_corto = clase['nombre'][:45] + '...' if len(clase['nombre']) > 45 else clase['nombre']
                html_tabla += f'''
                <td class="clase-cell">
                    <div class="codigo">{html.escape(clase['codigo'])}</div>
                    <div class="nombre">{html.escape(nombre_corto)}</div>
                </td>
                '''
            else:
                html_tabla += '<td class="vacio-cell">—</td>\n'
        html_tabla += '</tr>\n'
    
    html_tabla += '</tbody></table></div>'
    
    html_completo = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Horario - {html.escape(nombre_sala)}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1300px;
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
        .codigo {{ font-weight: bold; color: #e74c3c; font-size: 0.8rem; }}
        .nombre {{ font-weight: 500; color: #2c3e50; margin-top: 5px; font-size: 0.8rem; }}
        .vacio-cell {{ background: #f9f9f9; color: #ccc; text-align: center; }}
        .footer {{
            background: #ecf0f1;
            padding: 15px;
            text-align: center;
            font-size: 0.75rem;
            color: #7f8c8d;
        }}
        @media (max-width: 768px) {{
            .horario-table th, .horario-table td {{ padding: 6px; font-size: 0.7rem; }}
            .header h1 {{ font-size: 1.2rem; }}
        }}
        @media print {{
            body {{ background: white; padding: 0; }}
            .header {{ background: #2c3e50; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
        }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>📋 {html.escape(nombre_sala)}</h1>
        <p>Horario semanal actualizado</p>
        <div class="semana-badge">📅 {semana_actual}</div>
    </div>
    {html_tabla}
    <div class="footer">
        🗓️ Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')}
    </div>
</div>
</body>
</html>'''
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_completo)

def main():
    print("=" * 60)
    print("📖 GENERADOR DE HORARIOS - VERSIÓN CORREGIDA")
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
    
    for nombre_sala, horarios in salas.items():
        print(f"📝 Generando: {nombre_sala}")
        nombre_archivo = re.sub(r'[^\w\s]', '', nombre_sala)
        nombre_archivo = re.sub(r'\s+', '_', nombre_archivo)
        
        generar_html_sala(nombre_sala, horarios, salas_dir / f'{nombre_archivo}.html', SEMANA_ACTUAL)
        
        url = f"https://qrhorariosu-collab.github.io/QRhorarios/salas/{nombre_archivo}.html"
        qr = qrcode.make(url)
        qr.save(qrs_dir / f'{nombre_archivo}.png')
    
    # Index simple
    index_html = f'''<!DOCTYPE html>
<html>
<head><title>Horarios por Sala</title><meta charset="UTF-8"></head>
<body style="font-family:Arial;background:#f0f2f5;padding:20px">
<h1>🏫 Horarios por Sala - {SEMANA_ACTUAL}</h1>
<ul>
'''
    for nombre_sala in salas.keys():
        nombre_archivo = re.sub(r'[^\w\s]', '', nombre_sala)
        nombre_archivo = re.sub(r'\s+', '_', nombre_archivo)
        index_html += f'<li><a href="salas/{nombre_archivo}.html">{nombre_sala}</a> - <img src="qrs/{nombre_archivo}.png" width="80"></li>\n'
    
    index_html += f'</ul><p>Actualizado: {datetime.now()}</p></body></html>'
    
    with open(output_dir / 'index.html', 'w', encoding='utf-8') as f:
        f.write(index_html)
    
    print("\n" + "=" * 60)
    print("✅ ¡GENERACIÓN COMPLETADA!")
    print(f"📊 {len(salas)} salas procesadas")
    print(f"🌐 https://qrhorariosu-collab.github.io/QRhorarios/")
    print("=" * 60)

if __name__ == "__main__":
    main()