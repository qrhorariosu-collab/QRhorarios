import pandas as pd
import os

print("=" * 60)
print("DIAGNÓSTICO - LECTURA DE EXCEL")
print("=" * 60)

# Verificar que el archivo existe
if not os.path.exists('horarios.xlsx'):
    print("❌ No se encuentra horarios.xlsx")
    print(f"📁 Archivos en el directorio: {os.listdir('.')}")
    exit(1)

print("✅ Archivo horarios.xlsx encontrado")

# Leer el Excel
try:
    df = pd.read_excel('horarios.xlsx')
    print(f"\n✅ Excel cargado correctamente")
    print(f"📊 Forma: {df.shape[0]} filas, {df.shape[1]} columnas")
    print(f"\n📋 Columnas encontradas:")
    for col in df.columns:
        print(f"   - '{col}'")
    
    print(f"\n📋 Primeras 5 filas:")
    print(df.head())
    
    # Verificar si tiene la columna S10
    if 'S10' in df.columns:
        print(f"\n✅ Columna S10 encontrada")
        print(f"   Valores únicos en S10: {df['S10'].unique()}")
        activos = df[df['S10'] == 1]
        print(f"   Registros activos (S10=1): {len(activos)}")
    else:
        print(f"\n⚠️ No se encontró la columna S10")
        print(f"   Buscando columnas que empiecen con S...")
        s_columns = [c for c in df.columns if str(c).startswith('S')]
        print(f"   Columnas encontradas: {s_columns}")
    
    # Verificar salas
    if 'SALA' in df.columns:
        print(f"\n🏠 Salas encontradas:")
        for sala in df['SALA'].unique():
            if pd.notna(sala):
                count = len(df[df['SALA'] == sala])
                print(f"   - {sala}: {count} registros")
    else:
        print(f"\n❌ No se encuentra la columna 'SALA'")
        
except Exception as e:
    print(f"❌ Error al leer Excel: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)