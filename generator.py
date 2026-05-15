import pandas as pd
import qrcode
import re
from pathlib import Path
from datetime import datetime, time
import html
import os

def obtener_bloques_ocupados(hora_inicio, hora_fin):
    """Determina TODOS los bloques de 90 minutos que ocupa una clase"""
    # Bloques estándar de 90 minutos
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
        # Si la clase empieza antes o en el inicio del bloque y termina después del inicio
        if hora_inicio_str < bloque_fin and hora_fin_str > bloque_inicio:
            bloques_ocupados.append((bloque_inicio, bloque_fin, bloque_label))
    
    return bloques_ocupados

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
        
        # Crear estructura de horarios
        horarios = {}
        
        for _, row in df_sala.iterrows():
            hora_inicio = row['HORA INICIO']
            hora_fin = row['HORA FIN']
            dia = row['DIA']
            asignatura = row['ASIGNATURA']
            nombre = row['NOMBRE']
            
            # Obtener TODOS los bloques que ocupa esta clase
            bloques_ocupados = obtener_bloques_ocupados(hora_inicio, hora_fin)
            
            for bloque_inicio, bloque_fin, bloque_label in bloques_ocupados:
                clave_bloque = f"{bloque_inicio}_{bloque_fin}"
                hora_str = bloque_label
                
                if clave_bloque not in horarios:
                    horarios[clave_bloque] = {
                        'hora': hora_str,
                        'orden': int(bloque_inicio[:2]),
                        'clases': {}
                    }
                
                # Si ya hay una clase en este día y bloque, no sobrescribir (priorizar la primera)
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
    """Genera la página HTML para una sala"""
    
    # Solo días de Lunes a Viernes
    dias_orden = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
    
    # Ordenar bloques por hora
    bloques_ordenados = sorted(horarios.values(), key=lambda x: x['orden'])
    
    # Construir tabla
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
                
                # Mostrar BLOQUEO o clase normal
                if clase['codigo'] == 'BLOQUEO' or clase['nombre'] == 'BLOQUEO':
                    html_tabla += '<td class="bloqueo-cell">🔒 BLOQUEO</td>\n'
                else:
                    nombre_corto = clase['nombre'][:35] + '...' if len(clase['nombre']) > 35 else clase['nombre']
                    
                    # Indicar si es clase que ocupa múltiples bloques
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
            font-weight: 600;
            position: sticky;
            top: 0;
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
        .clase-cell {{
            background: #fafafa;
        }}
        .clase-cell.multibloque {{
            background: #e8f4fd;
            border-left: 3px solid #3498db;
        }}
        .codigo {{
            font-weight: bold;
            color: #e74c3c;
            font-size: 0.8rem;
        }}
        .nombre {{
            font-weight: 500;
            color: #2c3e50;
            margin-top: 5px;
            font-size: 0.8rem;
            line-height: 1.3;
        }}
        .horario-ext {{
            font-size: 0.7rem;
            color: #e67e22;
            font-weight: normal;
            display: inline-block;
            margin-left: 5px;
        }}
        .bloqueo-cell {{
            background: #fff3cd;
            color: #856404;
            text-align: center;
            font-weight: bold;
        }}
        .vacio-cell {{
            background: #f9f9f9;
            color: #ccc;
            text-align: center;
        }}
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
            .codigo {{ font-size: 0.65rem; }}
            .nombre {{ font-size: 0.65rem; }}
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
        <br>
        🔄 Los horarios se actualizan automáticamente cada semana
    </div>
</div>
</body>
</html>'''
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_completo)

def main():
    print("=" * 60)
    print("📖 GENERADOR DE HORARIOS - CLASES MULTIBLOQUE")
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
    
    # Index
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