cfdi_query = """
    SELECT
        UUID,
        RFC_EMISOR,
        TIPO_CAMBIO,
        USO_CFDI as CFDI_USE,
        CONCEPTO_IVA,
        BASE_CFDI AS TOTAL_CONCEPTO,
        CONCEPTO_ID,
        TOTAL_MXN,
        TIPO_ESTATUS
    FROM DLL.SAT.REPORTE_BASICO_CONCEPTOS_IMPUESTOS   
    """

# cfdi_query = """
#     SELECT
#         *
#     FROM DLL.SAT.REPORTE_BASICO_IMPUESTOS rbi    
#     """