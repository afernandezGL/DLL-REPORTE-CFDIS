cfdi_query = """
    SELECT
        rff.UUID_PADRE as UUID,
        TASA,
        rbi.USO_CFDI CFDI_USE 
    FROM DLL.SAT.REPORTE_FACTURACION_FINAL rff
    LEFT JOIN DLL.SAT.REPORTE_BASICO_IMPUESTOS rbi
        ON rff.UUID_PADRE = rbi.UUID
    
    """

"WHERE FORMAT(rbi.FECHA, 'yyyy-MM') = %(period)s"