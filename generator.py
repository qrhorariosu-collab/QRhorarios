import pandas as pd
import qrcode
import re
from pathlib import Path
from datetime import datetime
import html

def parse_celda_horario(texto):
    """Extrae toda la información de una celda del Excel"""
    if pd.isna(texto) or texto == "" or str(texto).strip() == "":
        return None
    
    texto = str(texto)
    
    # Dividir por líneas
    lineas = texto.strip().split('\n')
    if len(lineas) < 3:
        return None
    
    # Línea 1: Código y nombre
    linea1 = lineas[0].strip()
    codigo_match = re.match(r'^([A-Z0-9]+-\d+)', linea1)
    codigo = codigo_match.group(1) if codigo_match else "S/C"
    nombre = linea1.replace(codigo, '').replace('|', '').strip()
    if nombre.startswith('...'):
        nombre = nombre[3:]  # Quitar los puntos suspensivos
    
    # Línea 2: Tipo, cupos, sala, ID
    linea2 = lineas[1].strip()
    tipo_match = re.search(r'(TEO|TEOPRA|LAB|AYU|SEM)\s*(\d+)?', linea2)
    tipo = tipo_match.group(0) if tipo_match else "S/T"
    
    cupos_match = re.search(r'\((\d+)\)', linea2)
    cupos = cupos_match.group(1) if cupos_match else "?"
    
    sala_match = re.search(r'F1SALA\d+\s*\(([^)]+)\)', linea2)
    cupos_sala = sala_match.group(1) if sala_match else "?"
    
    id_match = re.search(r'\|\s*(\d{7,10})', linea2)
    id_clase = id_match.group(1) if id_match else "?"
    
    # Línea 3: Profesor
    linea3 = lineas[2].strip() if len(lineas) > 2 else ""
    rut_match = re.search(r'^(\d{7,8}-[0-9K])', linea3)
    rut = rut_match.group(1) if rut_match else ""
    profesor = linea3.replace(rut, '').strip() if rut else linea3
    
    return {
        'codigo': codigo,
        'nombre': nombre[:80],
        'tipo': tipo,
        'cupos': cupos,
        'cupos_sala': cupos_sala,
        'id_clase': id_clase,
        'profesor': profesor[:60] if profesor else "Sin asignar"
    }

def leer_excel_completo(archivo):
    """Lee el Excel y extrae todas las salas con sus horarios"""
    df = pd.read_excel(archivo, header=None)
    
    salas = {}
    i = 0
    
    while i < len(df):
        celda = str(df.iloc[i, 0]) if pd.notna(df.iloc[i, 0]) else ""
        
        # Detectar sala
        if "Sala SALA" in celda:
            # Extraer nombre de sala
            nombre_sala = celda.replace("Sala", "").strip()
            nombre_sala = re.sub(r'\s*-\s*\[.*\]', '', nombre_sala)
            
            print(f"  📌 Procesando: {nombre_sala}")
            
            # Saltar línea de "Horas"
            i += 2
            if i >= len(df):
                break
                
            # Leer días (fila de encabezados)
            dias_fila = df.iloc[i]
            dias = []
            for col in range(1, 7):
                dia = str(dias_fila[col]) if pd.notna(dias_fila[col]) else ""
                dias.append(dia)
            i += 1
            
            # Inicializar estructura de horarios para esta sala
            horarios = {}
            
            # Leer filas de horarios
            while i < len(df):
                fila = df.iloc[i]
                hora_texto = str(fila[0]) if pd.notna(fila[0]) else ""
                
                # Si encontramos otra sala o línea vacía grande, salimos
                if "Sala SALA" in hora_texto:
                    break
                
                # Si es una hora válida (contiene ":" y números)
                if hora_texto and re.search(r'\d+:\d+:', hora_texto):
                    for col in range(1, 7):
                        if col-1 < len(dias) and dias[col-1]:
                            contenido = fila[col]
                            clase = parse_celda_horario(contenido)
                            if clase:
                                dia = dias[col-1]
                                if hora_texto not in horarios:
                                    horarios[hora_texto] = {}
                                horarios[hora_texto][dia] = clase
                i += 1
            
            if horarios:
                salas[nombre_sala] = horarios
            continue
        i += 1
    
    return salas

def generar_html_sala(nombre_sala, horarios, output_path):
    """Genera la página HTML para una sala con todos los datos"""
    
    dias_orden = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
    
    # Construir tabla
    html_tabla = '<div style="overflow-x: auto;"><table class="horario-table">\n'
    html_tabla += '<thead><tr><th>Horario</th>'
    for dia in dias_orden:
        html_tabla += f'<th>{dia}</th>'
    html_tabla += '</tr></thead><tbody>\n'
    
    for hora, clases_por_dia in sorted(horarios.items(), key=lambda x: int(x[0].split(':')[0])):
        html_tabla += f'<tr>\n<td class="hora-cell">{hora}</td>\n'
        for dia in dias_orden:
            if dia in clases_por_dia:
                clase = clases_por_dia[dia]
                html_tabla += f'''
                <td class="clase-cell">
                    <div class="codigo">{html.escape(clase['codigo'])}</div>
                    <div class="nombre">{html.escape(clase['nombre'])}</div>
                    <div class="tipo">{html.escape(clase['tipo'])} | Cupos: {clase['cupos']}</div>
                    <div class="profesor">{html.escape(clase['profesor'])}</div>
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
        .header p {{
            opacity: 0.9;
            font-size: 0.9rem;
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
        .tipo {{
            background: #e8e8e8;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.7rem;
            display: inline-block;
            margin: 4px 0;
        }}
        .profesor {{
            font-size: 0.7rem;
            color: #3498db;
            margin-top: 6px;
            font-style: italic;
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
            .codigo, .nombre {{
                font-size: 0.65rem;
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
    print("📖 Generador de Horarios - Leyendo Excel...")
    print("=" * 60)
    
    # Leer todas las salas
    salas = leer_excel_completo('horarios.xlsx')
    
    if not salas:
        print("❌ No se encontraron salas con horarios")
        return
    
    print(f"\n✅ Encontradas {len(salas)} salas con horarios:")
    for nombre in salas.keys():
        print(f"   - {nombre}")
    
    # Crear directorios
    Path('output/salas').mkdir(parents=True, exist_ok=True)
    Path('output/qrs').mkdir(parents=True, exist_ok=True)
    
    # Generar páginas y QRs
    for nombre_sala, horarios in salas.items():
        print(f"\n📝 Generando: {nombre_sala}")
        
        # Nombre para archivo
        nombre_archivo = re.sub(r'[^\w\s]', '', nombre_sala)
        nombre_archivo = re.sub(r'\s+', '_', nombre_archivo)
        
        # Generar HTML
        html_path = f'output/salas/{nombre_archivo}.html'
        generar_html_sala(nombre_sala, horarios, html_path)
        
        # Generar QR
        url = f"https://qrhorariosu-collab.github.io/QRhorarios/salas/{nombre_archivo}.html"
        qr = qrcode.make(url)
        qr.save(f'output/qrs/{nombre_archivo}.png')
        print(f"   ✅ QR generado")
    
    # Generar index.html
    index_html = '''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Horarios - Todas las Salas</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 {
            color: white;
            text-align: center;
            margin-bottom: 30px;
            font-size: 2rem;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 20px;
        }
        .card {
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
            transition: transform 0.2s;
            text-align: center;
        }
        .card:hover { transform: translateY(-5px); }
        .card h3 {
            background: #2c3e50;
            color: white;
            padding: 15px;
            font-size: 1rem;
        }
        .card img {
            width: 150px;
            margin: 20px auto;
            display: block;
        }
        .card a {
            display: block;
            background: #3498db;
            color: white;
            text-decoration: none;
            padding: 12px;
            margin: 15px;
            border-radius: 8px;
            font-weight: bold;
        }
        .card a:hover { background: #2980b9; }
        .footer {
            text-align: center;
            color: white;
            margin-top: 30px;
            padding: 20px;
        }
    </style>
</head>
<body>
<div class="container">
    <h1>🏫 Sistema de Horarios por Sala</h1>
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
        <p>📅 Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
        <p>🔲 Los códigos QR son permanentes - Escanea una sola vez</p>
        <p>✅ Sistema actualizado automáticamente desde Excel</p>
    </div>
</div>
</body>
</html>'''
    
    with open('output/index.html', 'w', encoding='utf-8') as f:
        f.write(index_html)
    
    print("\n" + "=" * 60)
    print("✅ ¡GENERACIÓN COMPLETADA!")
    print(f"📊 {len(salas)} salas procesadas")
    print("🌐 Sitio web: https://qrhorariosu-collab.github.io/QRhorarios/")
    print("=" * 60)

if __name__ == "__main__":
    main()