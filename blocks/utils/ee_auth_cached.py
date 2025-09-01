# Earth Engine Auth Caching (Placeholder, robust gegen fehlende EE-Installation)
def ee_try_init() -> str:
    try:
        import ee  # type: ignore
        try:
            ee.Initialize()
            return "ee initialized"
        except Exception:
            try:
                ee.Authenticate()
                ee.Initialize()
                return "ee authenticated+initialized"
            except Exception as e:
                return f"ee auth failed: {e}"
    except Exception:
        return "ee not installed"
