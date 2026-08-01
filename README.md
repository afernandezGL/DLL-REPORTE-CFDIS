# DLL Reporte CFDI

## Visión general

Este repositorio contiene un pipeline en Python para consolidar información de CFDI, Edicom y metadata en un único reporte en Excel para un periodo determinado. El flujo está estructurado alrededor de un script principal de orquestación, cargadores de datos, lógica de transformación, reglas de integración y una etapa de exportación.

## Objetivo de negocio

El proyecto busca producir un artefacto de reporte mensual que combine datasets relacionados con facturación provenientes de distintas fuentes en una vista unificada. En la práctica, el pipeline está diseñado para:

- cargar datos fuente crudos desde archivos locales y consultas SQL,
- normalizar y enriquecer los datos,
- aplicar reglas de negocio para comparación de estatus, manejo de moneda, normalización de conceptos y asignación de prefijos,
- exportar un reporte consolidado a Excel.

El código sugiere un caso de uso de reporting y reconciliación, más que una aplicación transaccional.

## Arquitectura técnica

La solución sigue una arquitectura sencilla tipo ETL:

1. Ingesta de datos
   - los archivos de metadata se leen desde la carpeta de metadata,
   - los datos de Edicom se leen desde archivos Excel,
   - los datos de CFDI se obtienen mediante consultas SQL.
2. Transformación
   - se estandarizan los nombres de columnas,
   - se convierten y enriquecen los campos de fecha,
   - se preparan datos de impuestos y uso para la lógica posterior.
3. Integración
   - se unen múltiples datasets,
   - se aplican reglas de negocio para generar campos de estatus, tipo de cambio, concepto y prefijo.
4. Exportación
   - el dataframe consolidado se escribe en un archivo Excel dentro de la carpeta de salida.

## Diagrama del flujo de datos

```text
CLI / entrada de usuario (--date)
        |
        v
scr/DLL-Pipeline.py
        |
        +--> scr/loader.py
        |       +--> archivos locales (data/metadata, data/edicom)
        |       +--> consultas SQL (data/sql/*.py)
        |       +--> scr/database.py
        |
        +--> scr/transformer.py
        |
        +--> scr/integration.py
        |
        +--> scr/export.py
                    |
                    v
            data/output/<period>/report.xlsx
```

## Estructura del repositorio

- config/: constantes de configuración y entorno.
- data/: directorios de datos de entrada y salida.
  - data/metadata/: archivos ZIP de metadata esperados por el loader.
  - data/edicom/: archivos Excel de Edicom esperados por el loader.
  - data/output/: reportes Excel generados.
  - data/sql/: definiciones de consultas SQL para CFDI.
- scr/: lógica de la aplicación.
  - scr/DLL-Pipeline.py: punto de entrada principal de la orquestación.
  - scr/loader.py: carga de datos desde archivos y SQL.
  - scr/transformer.py: normalización y transformación de campos.
  - scr/integration.py: integración con reglas de negocio y enriquecimiento de columnas.
  - scr/export.py: exportación a Excel.
  - scr/database.py: creación y cierre del engine de SQLAlchemy.
  - scr/models.py: nombres de columnas compartidos, mappings y reglas de prefijos.

## Dependencias entre módulos

- scr/DLL-Pipeline.py es el punto de entrada y orquesta el flujo completo.
- scr/loader.py depende de config/config.py, scr/database.py y los módulos SQL en data/sql/.
- scr/transformer.py depende de scr/models.py para definiciones de columnas y mappings.
- scr/integration.py depende de scr/models.py y utiliza el dataframe transformado generado por el pipeline.
- scr/export.py consume el dataframe consolidado y escribe la salida final en Excel.

## Configuración del entorno

### Versión de Python

El código usa type hints modernos como tuple[...] y list[str], por lo que Python 3.9 o superior es la base más segura.

### Dependencias

Se esperan dependencias instaladas desde requirements.txt. El código importa directamente:

- pandas
- numpy
- SQLAlchemy
- pymssql
- openpyxl
- python-dotenv

### Configuración de .env

El proyecto lee las siguientes variables de entorno desde config/config.py:

```env
DB_SERVER=<host de la base de datos>
DB_DATABASE=<nombre de la base de datos>
DB_USER=<usuario>
DB_PASSWORD=<contraseña>
DB_PORT=<puerto>
```

Estos valores deben proporcionarse localmente antes de que los loaders basados en SQL puedan funcionar.

## Configuración local

1. Crear y activar un entorno virtual de Python.
2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

3. Crear un archivo .env en la raíz del proyecto con las variables de base de datos listadas anteriormente.
4. Colocar los archivos de entrada en las carpetas esperadas:
   - data/metadata/<period>/ con un archivo ZIP que contenga archivos .csv o .txt.
   - data/edicom/<period>/ con un archivo .xlsx.
   - Las consultas SQL bajo data/sql/ se ejecutarán contra la base de datos configurada.

## Ejecución

### Desde la línea de comandos

Ejecutar el pipeline desde la raíz del repositorio:

```bash
python scr/DLL-Pipeline.py --date 2026_01
```

### Notas sobre el parámetro de fecha

El argumento CLI se recibe como --date. La lógica de validación del código usa el formato YYYY_MM, mientras que el texto de ayuda actual menciona YYYY-MM. Esta diferencia debería aclararse o alinearse en una futura revisión.

El archivo de salida se escribe en:

```text
data/output/<period>/
```

con un nombre que sigue el patrón utilizado en el código de exportación.

## Buenas prácticas de mantenimiento

- Mantener las reglas de negocio centralizadas en scr/integration.py y scr/models.py en lugar de dispersarlas entre módulos.
- Evitar hard-code de nombres de columnas en múltiples lugares cuando sea posible; usar los mappings de scr/models.py como fuente única de verdad.
- Documentar el contrato de datos para cada fuente de entrada, especialmente para los archivos de metadata y Edicom.
- Eliminar declaraciones temporales de depuración antes de pasar el código a producción.
- Fijar versiones de dependencias en requirements.txt para mejorar la reproducibilidad.
- Agregar pruebas automatizadas para la lógica de transformación e integración a medida que el proyecto crezca.

## Posibles puntos de extensión

La implementación actual es funcional para un flujo único de pipeline, pero las siguientes mejoras harían el proyecto más robusto y mantenible:

- parametrizar el nombrado de salidas y la selección de columnas,
- introducir pruebas unitarias e de integración,
- reemplazar los strings inline de SQL por plantillas versionadas o stored procedures,
- soportar fuentes de entrada adicionales o formatos de salida,
- agregar automatización CI/CD y scripts de despliegue.

## Notas importantes

- Este README se elaboró a partir del código y la estructura actual del repositorio.
- Algunos detalles, como el esquema exacto de la base de datos y las reglas de negocio completas, se infirieron de la implementación y deberían validarse con los sistemas fuente.
- No se encontró una suite de pruebas automatizadas ni un pipeline de CI en el repositorio al momento de esta actualización de documentación.