from datapub.etl.normalize import infer_tipo_from_nome, extract_uf_from_nome


def test_infer_tipo_from_nome():
    assert infer_tipo_from_nome("Prefeitura Municipal de X") == "municipal"
    assert infer_tipo_from_nome("Câmara dos Deputados") == "federal"
    assert infer_tipo_from_nome("Assembleia Legislativa do Estado do Pará") == "estadual"


def test_extract_uf_from_nome():
    assert extract_uf_from_nome("Assembleia Legislativa do Estado do Pará") == "PA"
    assert extract_uf_from_nome("Imprensa Oficial do Estado de São Paulo") == "SP"
    assert extract_uf_from_nome("Ministério da Fazenda") is None

