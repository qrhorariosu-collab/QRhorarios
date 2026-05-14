import pandas as pd
import re
import qrcode
from pathlib import Path
from datetime import datetime
import html

def parse_celda_horario(texto):
    """Extrae información de una celda como: 'EFIS152-18 | ...OLEIBOL Y BÁSQUETBOL\nTEO 1 (0) | F1SALA9 (94) | 1147420...'"""
    if pd.isna(texto) or texto == "" or texto == "---":
        return None
    
    texto = str(texto)
    
    # Patrón para extraer código (ej: EFIS152-18)
    codigo_match = re.search(r'^([A-Z0-9]+-\d+)', texto)
    codigo = codigo_match.group(1) if codigo_match else "S/C"
    
    # Extraer nombre de asignatura (entre código y tipo)
    lines = texto.split('\n')
    nombre = ""
    for line in lines:
        if 'TEO' in line or 'TEOPRA' in line or 'LAB' in line:
            break
        if codigo in line:
            nombre = line.replace(codigo, '').strip()
            nombre = re.sub(r'^\s*[\|]?\s*', '', nombre)
            break
    
    # Extraer tipo y cupos
    tipo_match = re.search(r'(TEO\s*\d+|TEOPRA\s*\d+|LAB\s*\d+|AYU\s*\d+|SEM\s*\d+)', texto)
    tipo = tipo_match.group(1) if tipo_match else "S/T"
    
    cupos_match = re.search(r'\((\d+)\)', texto)
    cupos = cupos_match.group(1) if cupos_match else "?"
    
    # Extraer profesor (RUT o nombre al final)
    profesor = "Sin asignar"
    rut_match = re.search(r'(\d{7,8}-\d|[A-Z\s]+$)', texto)
    if rut_match:
        posible_prof = rut_match.group(1).strip()
        if len(posible_prof) > 3 and not posible_prof.isdigit():
            profesor = posible_prof[:50]
    
    return {
        'codigo': codigo,
        'nombre': nombre[:60],
        'tipo': tipo,
        'cupos': cupos,
        'profesor': profesor
    }

def leer_excel_estructurado(archivo_excel):
    """Lee el Excel y devuelve dict con horarios por sala"""
    df = pd.read_excel(archivo_excel, header=None)
    
    salas = {}
    sala_actual = None
    horarios_fila = None  # Para guardar la lista de horas
    
    i = 0
    while i < len(df):
        fila = df.iloc[i]
        primera_celda = str(fila[0]) if pd.notna(fila[0]) else ""
        
        # Detectar inicio de sala: "Sala SALA X - [F1SALAX]"
        if "Sala SALA" in primera_celda:
            # Extraer nombre de sala (ej: "SALA 9 AUDITORIO")
            match = re.search(r'Sala (SALA \d+[^\[]*)', primera_celda)
            if match:
                sala_actual = match.group(1).strip()
                salas[sala_actual] = {
                    'nombre': sala_actual,
                    'horarios': {}
                }
                i += 2  # Saltar línea de sala y la de "Horas"
                # Leer fila de horas (días)
                if i < len(df):
                    dias_fila = df.iloc[i]
                    dias = [str(dias_fila[c]).strip() if pd.notna(dias_fila[c]) else "" 
                           for c in range(1, 7)]  # Columnas B-G (Lunes a Sábado)
                    i += 1
                    # Ahora leer los horarios
                    while i < len(df):
                        fila_horario = df.iloc[i]
                        hora_texto = str(fila_horario[0]) if pd.notna(fila_horario[0]) else ""
                        
                        # Si encontramos otra sala o línea vacía grande, salimos
                        if "Sala SALA" in hora_texto or (hora_texto == "" and pd.isna(fila_horario[1])):
                            break
                        
                        if hora_texto and ":" in hora_texto:  # Es una fila de horario
                            for col_idx in range(1, 7):  # Lunes a Sábado
                                dia = dias[col_idx-1] if col_idx-1 < len(dias) else ""
                                if dia and dia != "":
                                    contenido = fila_horario[col_idx]
                                    clase = parse_celda_horario(contenido)
                                    if clase:
                                        clave = f"{hora_texto}_{dia}"
                                        salas[sala_actual]['horarios'][clave] = {
                                            'hora': hora_texto,
                                            'dia': dia,
                                            'clase': clase
                                        }
                        i += 1
                    continue  # Volver al ciclo principal
        i += 1
    
    return salas

def generar_html_sala(sala_nombre, horarios_dict, output_path):
    """Genera página HTML para una sala"""
    
    # Orden de días
    dias_orden = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
    # Extraer horas únicas ordenadas
    horas = sorted(set([h['hora'] for h in horarios_dict.values()]), 
                  key=lambda x: int(x.split(':')[0]))
    
    # Construir tabla HTML
    html_tabla = '<table class="horario-table">\n'
    html_tabla += '<thead><tr><th>Horario</th>'
    for dia in dias_orden:
        if any(h['dia'] == dia for h in horarios_dict.values()):
            html_tabla += f'<th>{dia}</th>'
    html_tabla += '</tr></thead><tbody>\n'
    
    for hora in horas:
        html_tabla += f'<tr><td class="hora">{hora}</td>'
        for dia in dias_orden:
            clave = f"{hora}_{dia}"
            if clave in horarios_dict:
                clase = horarios_dict[clave]['clase']
                html_tabla += f'''
                <td class="clase">
                    <div class="codigo">{html.escape(clase['codigo'])}</div>
                    <div class="nombre">{html.escape(clase['nombre'])}</div>
                    <div class="detalle">
                        <span class="tipo">{html.escape(clase['tipo'])}</span>
                        <span class="cupos">Cupos: {clase['cupos']}</span>
                    </div>
                    <div class="profesor">{html.escape(clase['profesor'])}</div>
                </td>
                '''
            else:
                html_tabla += '<td class="vacio">-</td>'
        html_tabla += '</tr>\n'
    
    html_tabla += '</tbody></table>'
    
    # Plantilla HTML completa
    html_completo = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Horario - {html.escape(sala_nombre)}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 20px 40px rgba(0,0,0,0.2);
        }}
        .header {{
            background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2rem;
            margin-bottom: 10px;
        }}
        .header p {{
            opacity: 0.9;
        }}
        .horario-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .horario-table th {{
            background: #34495e;
            color: white;
            padding: 15px;
            font-weight: 600;
            position: sticky;
            top: 0;
        }}
        .horario-table td {{
            border: 1px solid #e0e0e0;
            padding: 12px;
            vertical-align: top;
        }}
        .hora {{
            background: #ecf0f1;
            font-weight: bold;
            text-align: center;
            width: 100px;
        }}
        .clase {{
            background: #f9f9f9;
        }}
        .codigo {{
            font-weight: bold;
            color: #e74c3c;
            font-size: 0.85rem;
        }}
        .nombre {{
            font-weight: 600;
            color: #2c3e50;
            margin: 5px 0;
            font-size: 0.9rem;
        }}
        .detalle {{
            display: flex;
            justify-content: space-between;
            gap: 10px;
            font-size: 0.75rem;
            color: #7f8c8d;
            margin: 5px 0;
        }}
        .tipo {{
            background: #e8e8e8;
            padding: 2px 6px;
            border-radius: 4px;
        }}
        .profesor {{
            font-size: 0.75rem;
            color: #3498db;
            margin-top: 5px;
            font-style: italic;
        }}
        .vacio {{
            background: #fafafa;
            color: #bdc3c7;
            text-align: center;
        }}
        .footer {{
            background: #ecf0f1;
            padding: 15px;
            text-align: center;
            font-size: 0.8rem;
            color: #7f8c8d;
        }}
        @media (max-width: 768px) {{
            .horario-table th, .horario-table td {{
                padding: 6px;
                font-size: 0.7rem;
            }}
            .header h1 {{
                font-size: 1.3rem;
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
        <h1>📋 {html.escape(sala_nombre)}</h1>
        <p>Horario semanal actualizado</p>
    </div>
    <div style="overflow-x: auto;">
        {html_tabla}
    </div>
    <div class="footer">
        🗓️ Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')}
    </div>
</div>
</body>
</html>'''
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_completo)

def main():
    print("📖 Leyendo archivo Excel...")
    salas = leer_excel_estructurado('horarios.xlsx')
    
    if not salas:
        print("❌ No se encontraron salas en el archivo")
        return
    
    print(f"✅ Encontradas {len(salas)} salas")
    
    # Crear carpetas
    Path('output/salas').mkdir(parents=True, exist_ok=True)
    Path('output/qrs').mkdir(parents=True, exist_ok=True)
    
    # Generar página para cada sala
    for sala_nombre, sala_data in salas.items():
        print(f"   Generando {sala_nombre}...")
        # Limpiar nombre para archivo
        nombre_archivo = re.sub(r'[^\w\-_\. ]', '_', sala_nombre)
        nombre_archivo = re.sub(r'\s+', '_', nombre_archivo)
        
        # Generar HTML
        html_path = f'output/salas/{nombre_archivo}.html'
        generar_html_sala(sala_nombre, sala_data['horarios'], html_path)
        
        # Generar QR
        url = f"https://qrhorariosu-collab.github.io/QRhorarios/salas/{nombre_archivo}.html""
        qr = qrcode.make(url)
        qr_path = f'output/qrs/{nombre_archivo}.png'
        qr.save(qr_path)
        print(f"      QR generado: {qr_path}")
    
    # Generar index con lista de salas
    index_html = '''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Lista de Salas - Horarios</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f0f2f5; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #2c3e50; text-align: center; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px; margin-top: 30px; }
        .card { background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.1); text-align: center; transition: transform 0.2s; }
        .card:hover { transform: translateY(-5px); }
        .card img { width: 100%; max-width: 150px; margin: 15px auto; display: block; }
        .card h3 { background: #3498db; color: white; padding: 10px; margin: 0; }
        .card a { display: block; padding: 10px; background: #ecf0f1; color: #2c3e50; text-decoration: none; margin: 10px; border-radius: 5px; }
        .card a:hover { background: #3498db; color: white; }
    </style>
</head>
<body>
<div class="container">
    <h1>🏫 Selecciona tu Sala</h1>
    <div class="grid">
'''
    
    for sala_nombre in salas.keys():
        nombre_archivo = re.sub(r'[^\w\-_\. ]', '_', sala_nombre)
        nombre_archivo = re.sub(r'\s+', '_', nombre_archivo)
        index_html += f'''
        <div class="card">
            <h3>{html.escape(sala_nombre)}</h3>
            <img src="qrs/{nombre_archivo}.png" alt="QR">
            <a href="salas/{nombre_archivo}.html">Ver Horario</a>
        </div>
'''
    
    index_html += '''
    </div>
</div>
</body>
</html>
'''
    
    with open('output/index.html', 'w', encoding='utf-8') as f:
        f.write(index_html)
    
    print(f"\n✅ Generación completa! {len(salas)} salas procesadas.")
    print("📂 Los archivos están en la carpeta 'output/'")

if __name__ == "__main__":
    main()