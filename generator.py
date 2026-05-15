import pandas as pd
import qrcode
import re
from pathlib import Path
from datetime import datetime
import html
import os

def agrupar_bloques_horarios(df_sala):
    """
    Agrupa las clases que pertenecen al mismo bloque horario
    Ej: 8:10-8:55 y 8:55-9:40 se agrupan en 8:10-9:40
    """
    # Definir los bloques completos (hora_inicio, hora_fin)
    bloques = [
        ("08:10:00", "09:40:00"),
        ("09:50:00", "11:20:00"),
        ("11:30:00", "13:00:00"),
        ("14:10:00", "15:40:00"),
        ("15:50:00", "17:20:00"),
        ("17:30:00", "19:00:00"),
        ("19:10:00", "20:40:00"),
    ]
    
    # Mapeo de rangos cortos a bloque completo
    mapeo_bloques = {}
    for bloque_inicio, bloque_fin in bloques:
        # Extraer hora numérica para ordenar
        hora_num = int(bloque_inicio.split(':')[0])
        
        # Asignar rangos de 45 minutos a este bloque
        rango1_inicio = bloque_inicio
        rango1_fin = f"{int(bloque_inicio.split(':')[0])}:{int(bloque_inicio.split(':')[1]) + 45}:00"
        
        rango2_inicio = rango1_fin
        rango2_fin = bloque_fin
        
        mapeo_bloques[(rango1_inicio, rango1_fin)] = (bloque_inicio, bloque_fin, hora_num)
        mapeo_bloques[(rango2_inicio, rango2_fin)] = (bloque_inicio, bloque_fin, hora_num)
    
    # Agrupar por bloque
    bloques_agrupados = {}
    
    for _, row in df_sala.iterrows():
        hora_inicio = row['HORA INICIO']
        hora_fin = row['HORA FIN']
        dia = row['DIA']
        asignatura = row['ASIGNATURA']
        nombre = row['NOMBRE']
        
        # Buscar a qué bloque pertenece
        bloque_info = None
        for (r_inicio, r_fin), (b_inicio, b_fin, hora_num) in mapeo_bloques.items():
            if r_inicio == hora_inicio and r_fin == hora_fin:
                bloque_info = (b_inicio, b_fin, hora_num)
                break
        
        if bloque_info:
            b_inicio, b_fin, hora_num = bloque_info
            clave_bloque = f"{b_inicio}_{b_fin}"
            
            if clave_bloque not in bloques_agrupados:
                bloques_agrupados[clave_bloque] = {
                    'hora_inicio': b_inicio,
                    'hora_fin': b_fin,
                    'hora_num': hora_num,
                    'clases': {}
                }
            
            # Si ya hay una clase en este día, solo actualizar si no es BLOQUEO
            if dia in bloques_agrupados[clave_bloque]['clases']:
                existing = bloques_agrupados[clave_bloque]['clases'][dia]
                # Si la nueva no es BLOQUEO y la actual sí, reemplazar
                if asignatura != 'BLOQUEO' and existing['codigo'] == 'BLOQUEO':
                    bloques_agrupados[clave_bloque]['clases'][dia] = {
                        'codigo': asignatura,
                        'nombre': nombre
                    }
            else:
                bloques_agrupados[clave_bloque]['clases'][dia] = {
                    'codigo': asignatura,
                    'nombre': nombre
                }
    
    return bloques_agrupados

def leer_excel_semanas(archivo_excel, semana_actual="S10"):
    """
    Lee el Excel con formato de tabla plana
    """
    print(f"📖 Leyendo archivo: {archivo_excel}")
    df = pd.read_excel(archivo_excel)
    
    # Verificar columnas necesarias
    columnas_necesarias = ['ASIGNATURA', 'NOMBRE', 'DIA', 'HORA INICIO', 'HORA FIN', 'SALA']
    for col in columnas_necesarias:
        if col not in df.columns:
            print(f"❌ Error: No se encuentra la columna '{col}'")
            print(f"📋 Columnas disponibles: {list(df.columns)}")
            return {}
    
    # Filtrar por semana actual
    col_semana = semana_actual
    if col_semana in df.columns:
        df_activo = df[df[col_semana] == 1].copy()
        print(f"✅ Filtrado por {semana_actual}: {len(df_activo)} registros activos")
    else:
        print(f"⚠️ No se encuentra la columna {semana_actual}, usando todos los registros")
        df_activo = df.copy()
    
    # Agrupar por sala
    salas = {}
    
    for sala in df_activo['SALA'].unique():
        if pd.isna(sala):
            continue
        
        df_sala = df_activo[df_activo['SALA'] == sala]
        print(f"  📌 Procesando sala: {sala} ({len(df_sala)} registros)")
        
        # Agrupar por bloques horarios
        bloques = agrupar_bloques_horarios(df_sala)
        
        if bloques:
            salas[sala] = bloques
    
    return salas

def generar_html_sala(nombre_sala, bloques, output_path, semana_actual):
    """Genera la página HTML para una sala"""
    
    # Orden de días
    dias_orden = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
    
    # Ordenar bloques por hora
    bloques_ordenados = sorted(bloques.values(), key=lambda x: x['hora_num'])
    
    # Construir tabla
    html_tabla = '<div style="overflow-x: auto;"><table class="horario-table">\n'
    html_tabla += '<thead><tr><th>Horario</th>'
    for dia in dias_orden:
        html_tabla += f'<th>{dia}</th>'
    html_tabla += '</tr></thead><tbody>\n'
    
    for bloque in bloques_ordenados:
        hora_str = f"{bloque['hora_inicio'][:5]} - {bloque['hora_fin'][:5]}"
        html_tabla += f'<tr><td class="hora-cell">{hora_str}</td>\n'
        
        for dia in dias_orden:
            if dia in bloque['clases']:
                clase = bloque['clases'][dia]
                # Si es BLOQUEO, mostrarlo como vacío o con texto especial
                if clase['codigo'] == 'BLOQUEO' or clase['nombre'] == 'BLOQUEO':
                    html_tabla += '<td class="vacio-cell">—</td>\n'
                else:
                    # Truncar nombre si es muy largo
                    nombre_corto = clase['nombre'][:50] + '...' if len(clase['nombre']) > 50 else clase['nombre']
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
    
    # HTML completo
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
        .header h1 {{
            font-size: 1.8rem;
            margin-bottom: 5px;
        }}
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
            .horario-table th, .horario-table td {{
                padding: 6px;
                font-size: 0.7rem;
            }}
            .header h1 {{
                font-size: 1.2rem;
            }}
            .codigo {{ font-size: 0.65rem; }}
            .nombre {{ font-size: 0.65rem; }}
        }}
        @media print {{
            body {{ background: white; padding: 0; }}
            .header {{ background: #2c3e50; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
            .clase-cell {{ break-inside: avoid; }}
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

def generar_index(salas, semana_actual, output_dir):
    """Genera la página principal"""
    
    index_html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Horarios - Todas las Salas</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{
            color: white;
            text-align: center;
            margin-bottom: 10px;
            font-size: 2rem;
        }}
        .semana-info {{
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }}
        .semana-badge {{
            background: #e74c3c;
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 20px;
        }}
        .card {{
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
            transition: transform 0.2s;
            text-align: center;
        }}
        .card:hover {{ transform: translateY(-5px); }}
        .card h3 {{
            background: #2c3e50;
            color: white;
            padding: 15px;
            font-size: 1rem;
        }}
        .card img {{
            width: 150px;
            margin: 20px auto;
            display: block;
        }}
        .card a {{
            display: block;
            background: #3498db;
            color: white;
            text-decoration: none;
            padding: 12px;
            margin: 15px;
            border-radius: 8px;
            font-weight: bold;
        }}
        .card a:hover {{ background: #2980b9; }}
        .footer {{
            text-align: center;
            color: white;
            margin-top: 30px;
            padding: 20px;
        }}
    </style>
</head>
<body>
<div class="container">
    <h1>🏫 Sistema de Horarios por Sala</h1>
    <div class="semana-info">
        <span class="semana-badge">📅 Semana {semana_actual}</span>
    </div>
    <div class="grid">
'''
    
    for nombre_sala in salas.keys():
        nombre_archivo = re.sub(r'[^\w\s]', '', nombre_sala)
        nombre_archivo = re.sub(r'\s+', '_', nombre_archivo)
        index_html += f'''
        <div class="card">
            <h3>{html.escape(nombre_sala)}</h3>
            <img src="qrs/{nombre_archivo}.png" alt="QR">
            <a href="salas/{nombre_archivo}.html">📅 Ver Horario</a>
        </div>'''
    
    index_html += f'''
    </div>
    <div class="footer">
        <p>🔲 Los códigos QR son permanentes - Escanea una sola vez</p>
        <p>✅ Actualizado automáticamente desde Excel - Semana {semana_actual}</p>
        <p>📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
    </div>
</div>
</body>
</html>'''
    
    with open(output_dir / 'index.html', 'w', encoding='utf-8') as f:
        f.write(index_html)

def main():
    print("=" * 60)
    print("📖 GENERADOR DE HORARIOS - CON AGRUPACIÓN DE BLOQUES")
    print("=" * 60)
    
    # Configuración
    ARCHIVO_EXCEL = 'horarios.xlsx'
    SEMANA_ACTUAL = 'S10'  # Cambia según la semana
    
    if not os.path.exists(ARCHIVO_EXCEL):
        print(f"❌ Error: No se encuentra {ARCHIVO_EXCEL}")
        return
    
    salas = leer_excel_semanas(ARCHIVO_EXCEL, SEMANA_ACTUAL)
    
    if not salas:
        print("❌ No se encontraron salas con horarios")
        return
    
    print(f"\n✅ Encontradas {len(salas)} salas")
    
    # Crear directorios
    output_dir = Path('output')
    salas_dir = output_dir / 'salas'
    qrs_dir = output_dir / 'qrs'
    
    salas_dir.mkdir(parents=True, exist_ok=True)
    qrs_dir.mkdir(parents=True, exist_ok=True)
    
    # Generar archivos
    for nombre_sala, bloques in salas.items():
        print(f"📝 Generando: {nombre_sala}")
        nombre_archivo = re.sub(r'[^\w\s]', '', nombre_sala)
        nombre_archivo = re.sub(r'\s+', '_', nombre_archivo)
        
        generar_html_sala(nombre_sala, bloques, salas_dir / f'{nombre_archivo}.html', SEMANA_ACTUAL)
        
        url = f"https://qrhorariosu-collab.github.io/QRhorarios/salas/{nombre_archivo}.html"
        qr = qrcode.make(url)
        qr.save(qrs_dir / f'{nombre_archivo}.png')
    
    generar_index(salas, SEMANA_ACTUAL, output_dir)
    
    print("\n" + "=" * 60)
    print("✅ ¡GENERACIÓN COMPLETADA!")
    print(f"📊 {len(salas)} salas procesadas")
    print(f"📅 Semana: {SEMANA_ACTUAL}")
    print("🌐 https://qrhorariosu-collab.github.io/QRhorarios/")
    print("=" * 60)

if __name__ == "__main__":
    main()