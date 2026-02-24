def test_import_package():
    import lakehouse_mlops_aiops_lab  # noqa: F401

    assert lakehouse_mlops_aiops_lab is not None


def test_basic_math():
    assert 1 + 1 == 2
