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
        TIPO_ESTATUS,
        FECHA,
        TIPO_COMPROBANTE,
        TOTAL as TOTAL_FACTURA,
        SUBTOTAL as SUBTOTAL_FACTURA, 
        SUBTOTAL_MXN as SUBTOTAL_FACTURA_MXN
    FROM DLL.SAT.REPORTE_BASICO_CONCEPTOS_IMPUESTOS
        WHERE YEAR(FECHA) = {year}
        AND RFC_EMISOR IN ({rfc_emisor_list})
        AND TIPO_COMPROBANTE IN ('I')
        AND TIPO = 'EMITIDOS'
    """

full_cfdi_query = """
    SELECT
        RFC_REGISTRO,
        UUID,
        FECHA,
        SERIE,
        FOLIO,
        RFC_EMISOR,
        NOMBRE_EMISOR,
        REGIMEN_FISCAL,
        RFC_RECEPTOR,
        NOMBRE_RECEPTOR,
        USO_CFDI,
        SUBTOTAL,
        DESCUENTO,
        TOTAL,
        MONEDA,
        TIPO_CAMBIO,
        SUBTOTAL_MXN,
        TOTAL_MXN,
        TIPO_COMPROBANTE,
        LUGAR_EXPEDICION,
        METODO_PAGO,
        FORMA_PAGO,
        VERSION,
        TIPO,
        TIPO_ESTATUS,
        CFDI_SUSTITUIDO,
        CONCEPTO_ID,
        CLAVE_PROD_SERV,
        PROD_SERV,
        CANTIDAD,
        CLAVE_UNIDAD,
        UNIDAD,
        DESCRIPCION,
        OBJETO_IMP,
        VALOR_UNITARIO,
        IMPORTE,
        DESCUENTO_CONC,
        CONCEPTO_IVA,
        BASE_CFDI,
        IMPUESTO_CFDI
    FROM DLL.SAT.REPORTE_BASICO_CONCEPTOS_IMPUESTOS
        WHERE YEAR(FECHA) = {year}
        AND RFC_EMISOR IN ({rfc_emisor_list})
        AND UUID IN ({uuid_list})
        AND TIPO_COMPROBANTE IN ('I')
        AND TIPO = 'EMITIDOS'
    """