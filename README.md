# DLL
Tabla de DLL

## Paso 1:
```python
pip install pandas numpy sqlalchemy datetime
```
Navegar a la ubicación del script
```bash
cd DLL\
```
En cada ejercicio se deben de cambiar el archivo de Facturación del Mes:
```python
data = pd.read_excel('REPORTE FACTURACIÓN - ENERO 2026.xlsx')
```


Y los archivos de la metadata en:
```python
meta1 = pd.read_csv(
    r'C:\Users\AnthonyArenas\Proyectos\DLL\Metadata\0DF84719-D342-4888-9EA2-D79DA4FE3682_01.txt', 
    sep='~'
)

meta2 = pd.read_csv(
    r'C:\Users\AnthonyArenas\Proyectos\DLL\Metadata\3E8C8FF2-15A2-48BB-85F9-0DDA70D7E8D9_01.txt', 
    sep='~'
)

meta3 = pd.read_csv(
    r'C:\Users\AnthonyArenas\Proyectos\DLL\Metadata\DCBE91DD-58F2-47B2-B289-76AA1A3CDE11_01.txt', 
    sep='~'
)

meta4 = pd.read_csv(
    r'C:\Users\AnthonyArenas\Proyectos\DLL\Metadata\6CA57674-E72A-478B-B088-690AB454DB25_01.txt', 
    sep='~'
)

meta5 = pd.read_csv(
    r'C:\Users\AnthonyArenas\Proyectos\DLL\Metadata\1DD73245-6482-45EB-B61A-904675C4F505_01.txt', 
    sep='~'
)

meta6 = pd.read_csv(
    r'C:\Users\AnthonyArenas\Proyectos\DLL\Metadata\659A874C-1D79-49F2-B1CB-9246750EAB54_01.txt', 
    sep='~'
)
```


Ejecutar script:
```python
python DLL-Pipeline.py
```
