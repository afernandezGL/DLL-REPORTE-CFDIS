# DLL Reporte CFDI

## Introducción

Este repositorio contiene un pipeline en Python para consolidar información de CFDI, Edicom y metadata en un reporte Excel mensual. El objetivo es unir distintas fuentes de datos y generar una vista de negocio que permita revisar, comparar y analizar información de facturación de manera más sencilla.

No es una aplicación web ni un servicio en ejecución continua. Es un flujo de procesamiento por línea de comandos, pensado para ejecutarse de forma local o en entornos de automatización controlados.

## Qué hace este proyecto

El flujo está diseñado para:

- leer datos fuente desde archivos locales y consultas SQL,
- normalizar y transformar los datos a un formato consistente,
- aplicar reglas de negocio para enriquecer la información,
- consolidar los datasets en un único DataFrame,
- exportar el resultado a Excel para su revisión.

En términos de arquitectura, el proyecto sigue un patrón ETL simple:

1. Ingesta
2. Transformación
3. Integración
4. Exportación

## Requisitos previos

Antes de ejecutar el proyecto, asegúrate de tener lo siguiente:

- Python 3.9 o superior
- pip actualizado
- acceso a una base de datos configurada para las consultas SQL
- una conexión activa a la base de datos desde el entorno donde se ejecuta el pipeline
- los archivos de entrada colocados en las carpetas correspondientes dentro de la estructura del repositorio

## Estructura del repositorio

- config/: configuración y variables de entorno
- data/: datos de entrada y salida
  - data/metadata/: archivos de metadata esperados por el loader
  - data/edicom/: archivos fuente de Edicom
  - data/output/: reportes generados en Excel
  - data/sql/: consultas SQL utilizadas por el pipeline
- scr/: lógica principal del proyecto
  - scr/report-pipeline.py: punto de entrada del flujo
  - scr/orchestrator.py: orquestación del pipeline
  - scr/loader.py: carga de datos desde archivos y base de datos
  - scr/transformer.py: normalización y enriquecimiento de campos
  - scr/integration.py: reglas de negocio y consolidación
  - scr/export.py: exportación a Excel
  - scr/database.py: configuración del engine SQLAlchemy
  - scr/models.py: mappings, columnas compartidas y reglas de prefijos
  - scr/styles.py: estilos visuales para los reportes
- tests/: pruebas automatizadas para la lógica de integración y transformación

## Instalación paso a paso

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd DLL-REPORTE-CFDIS
```

### 2. Crear un entorno virtual

```bash
python -m venv .venv
```

Activarlo en Windows:

```bash
.venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Crear el archivo de configuración

El proyecto lee variables desde un archivo .env en la raíz del repositorio. Crea uno con el siguiente contenido:

```env
DB_SERVER=<host de la base de datos>
DB_DATABASE=<nombre de la base de datos>
DB_USER=<usuario>
DB_PASSWORD=<contraseña>
DB_PORT=<puerto>
```

Estas variables son necesarias para que las consultas SQL funcionen correctamente. Además, es obligatorio que exista una conexión accesible a la base de datos configurada desde el entorno donde se ejecuta el proyecto.

## Preparación de datos de entrada

Antes de ejecutar el pipeline, asegúrate de dejar los datos en las rutas esperadas:

- data/metadata/<periodo>/: archivos que el loader pueda procesar
- data/edicom/<periodo>/: archivos fuente de Edicom
- data/sql/: consultas SQL definidas para CFDI

La estructura de carpetas debe mantenerse consistente con la lógica del loader.

## Ejecución del pipeline

Desde la raíz del proyecto, ejecuta:

```bash
python -m scr.report_pipeline --date 2026_01 --format cliente
```

### Nota importante sobre la fecha

El parámetro esperado por el código es en formato YYYY_MM. Por ejemplo:

- 2026_01
- 2026_02
- 2026_04

Aunque el texto de ayuda puede mostrar un formato distinto, la validación del script espera el formato con guion bajo.

## Salida esperada

Si el proceso termina correctamente, el reporte se generará en la carpeta:

```text
data/output/<periodo>/
```

El resultado final se exporta en formato Excel y queda listo para revisión.

## Flujo interno del proyecto

```text
CLI (--date)
  |
  v
scr/report-pipeline.py
  |
  +--> scr/orchestrator.py
  |      +--> scr/loader.py
  |      +--> archivos locales
  |      +--> consultas SQL
  |      +--> scr/database.py
  |
  +--> scr/transformer.py
  |
  +--> scr/integration.py
  |
  +--> scr/export.py

```

## Pruebas

El repositorio incluye pruebas básicas para validar la lógica de integración y normalización:

```bash
pytest
```

Estas pruebas ayudan a proteger reglas de negocio críticas y a evitar regresiones cuando el código cambia.

## Buenas prácticas de desarrollo

Para mantener el proyecto estable y fácil de extender:

- centralizar las reglas de negocio en los módulos de integración y modelos,
- evitar duplicar nombres de columnas o transformaciones en varios lugares,
- documentar los contratos de entrada cuando cambien las fuentes de datos,
- mantener las dependencias reproducibles mediante requirements.txt,
- revisar y limpiar logs temporales antes de pasar cambios a producción.

## Troubleshooting

### Error: ModuleNotFoundError

Esto suele pasar cuando el entorno virtual no está activado o las dependencias no se instalaron correctamente.

Solución:

```bash
pip install -r requirements.txt
```

### Error: fecha inválida

El formato correcto es YYYY_MM, por ejemplo 2026_01.

### Error de conexión a base de datos

Verifica que las variables de entorno en .env sean correctas y que el host, puerto y credenciales sean válidos. También es necesario que exista una conexión activa a la base de datos desde el entorno donde se ejecuta el pipeline.

### No se genera el archivo de salida

Revisa que:

- los datos de entrada existan en las carpetas esperadas,
- el periodo solicitado sea válido,
- el proceso no haya terminado con errores antes de la exportación.

## Notas finales

Este README fue pensado para que una persona nueva en el proyecto pueda entender rápidamente qué hace el repositorio, cómo configurarlo y cómo ejecutarlo. Si el proyecto crece, conviene seguir mejorando la documentación de cada fuente de datos, así como agregar más pruebas y automatización de despliegue.