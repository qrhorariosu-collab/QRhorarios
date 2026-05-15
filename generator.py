import pandas as pd
import qrcode
import re
from pathlib import Path
from datetime import datetime
import html
import os

def leer_excel_semanas(archivo_excel, semana_actual="S10"):
    """
    Lee el Excel con formato de tabla plana
    Columnas: ASIGNATURA, NOMBRE, DIA, HORA INICIO, HORA FIN, SALA, S10, etc.
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
    
    # Filtrar por semana actual (columna como S10, S11, etc.)
    col_semana = semana_actual
    if col_semana in df.columns:
        df = df[df[col_semana] == 1]
        print(f"✅ Filtrado por {semana_actual}: {len(df)} registros activos")
    else:
        print(f"⚠️ No se encuentra la columna {semana_actual}, usando todos los registros")
    
    # Agrupar por sala
    salas = {}
    
    for sala in df['SALA'].unique():
        if pd.isna(sala):
            continue
            
        df_sala = df[df['SALA'] == sala]
        print(f"  📌 Procesando sala: {sala} ({len(df_sala)} clases)")
        
        horarios = {}
        
        for _, row in df_sala.iterrows():
            dia = row['DIA']
            hora_inicio = row['HORA INICIO']
            hora_fin = row['HORA FIN']
            asignatura = row['ASIGNATURA']
            nombre = row['NOMBRE']
            
            # Formatear hora para mostrar
            hora_str = f"{hora_inicio} - {hora_fin}"
            
            # Crear clave única
            clave_hora = f"{hora_inicio}_{hora_fin}"
            
            if clave_hora not in horarios:
                horarios[clave_hora] = {'hora': hora_str, 'clases': {}}
            
            horarios[clave_hora]['clases'][dia] = {
                'codigo': asignatura,
                'nombre': nombre
            }
        
        salas[sala] = horarios
    
    return salas

def generar_html_sala(nombre_sala, horarios, output_path, semana_actual):
    """Genera la página HTML para una sala"""
    
    # Orden de días
    dias_orden = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
    
    # Ordenar horas
    horas_ordenadas = sorted(horarios.keys(), key=lambda x: int(x.split('_')[0].split(':')[0]))
    
    # Construir tabla
    html_tabla = '<div style="overflow-x: auto;"><table class="horario-table">\n'
    html_tabla += '<thead><tr><th>Horario</th>'
    for dia in dias_orden:
        html_tabla += f'<th>{dia}</th>'
    html_tabla += '</tr></thead><tbody>\n'
    
    for hora_key in horas_ordenadas:
        hora_info = horarios[hora_key]
        html_tabla += f'<tr><td class="hora-cell">{hora_info["hora"]}</td>\n'
        
        for dia in dias_orden:
            if dia in hora_info['clases']:
                clase = hora_info['clases'][dia]
                html_tabla += f'''
                <td class="clase-cell">
                    <div class="codigo">{html.escape(clase['codigo'])}</div>
                    <div class="nombre">{html.escape(clase['nombre'])}</div>
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
            border: 1px solid #e0e0e0;
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
            min-width: 180px;
        }}
        .codigo {{
            font-weight: bold;
            color: #e74c3c;
            font-size: 0.8rem;
        }}
        .nombre {{
            font-weight: 600;
            color: #2c3e50;
            margin: 6px 0;
            font-size: 0.85rem;
        }}
        .vacio-cell {{
            background: #f5f5f5;
            color: #bdc3c7;
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
                padding: 5px;
                font-size: 0.7rem;
            }}
            .header h1 {{
                font-size: 1.2rem;
            }}
        }}
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            .header {{
                background: #2c3e50;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}
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
    """Genera la página principal con todas las salas"""
    
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
            font-size: 1.1rem;
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
    print("📖 GENERADOR DE HORARIOS - FORMATO TABLA PLANA")
    print("=" * 60)
    
    # Configuración
    ARCHIVO_EXCEL = 'horarios.xlsx'
    SEMANA_ACTUAL = 'S10'  # Cambia esto según la semana que quieras mostrar
    
    # Verificar que el archivo existe
    if not os.path.exists(ARCHIVO_EXCEL):
        print(f"❌ Error: No se encuentra el archivo {ARCHIVO_EXCEL}")
        print("📄 Asegúrate de subir el archivo Excel con el formato correcto")
        return
    
    # Leer Excel
    salas = leer_excel_semanas(ARCHIVO_EXCEL, SEMANA_ACTUAL)
    
    if not salas:
        print("❌ No se encontraron salas con horarios")
        print("Verifica que el Excel tenga las columnas: ASIGNATURA, NOMBRE, DIA, HORA INICIO, HORA FIN, SALA")
        return
    
    print(f"\n✅ Encontradas {len(salas)} salas con horarios")
    
    # Crear directorios
    output_dir = Path('output')
    salas_dir = output_dir / 'salas'
    qrs_dir = output_dir / 'qrs'
    
    salas_dir.mkdir(parents=True, exist_ok=True)
    qrs_dir.mkdir(parents=True, exist_ok=True)
    
    # Generar páginas y QRs
    for nombre_sala, horarios in salas.items():
        print(f"\n📝 Generando: {nombre_sala}")
        
        # Limpiar nombre
        nombre_archivo = re.sub(r'[^\w\s]', '', nombre_sala)
        nombre_archivo = re.sub(r'\s+', '_', nombre_archivo)
        
        # Generar HTML
        html_path = salas_dir / f'{nombre_archivo}.html'
        generar_html_sala(nombre_sala, horarios, html_path, SEMANA_ACTUAL)
        
        # Generar QR
        url = f"https://qrhorariosu-collab.github.io/QRhorarios/salas/{nombre_archivo}.html"
        qr = qrcode.make(url)
        qr.save(qrs_dir / f'{nombre_archivo}.png')
        print(f"   ✅ QR generado")
    
    # Generar index
    generar_index(salas, SEMANA_ACTUAL, output_dir)
    
    print("\n" + "=" * 60)
    print("✅ ¡GENERACIÓN COMPLETADA!")
    print(f"📊 {len(salas)} salas procesadas")
    print(f"📅 Semana actual: {SEMANA_ACTUAL}")
    print("🌐 Sitio web: https://qrhorariosu-collab.github.io/QRhorarios/")
    print("=" * 60)
    
    # Mostrar resumen de archivos creados
    print("\n📂 Archivos generados:")
    print(f"   - output/index.html")
    print(f"   - output/salas/ ({len(salas)} archivos)")
    print(f"   - output/qrs/ ({len(salas)} códigos QR)")

if __name__ == "__main__":
    main()