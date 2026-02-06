import logging

dispatch_en = None
dispatch_de = None
dispatch_ar = None

try:
    from .en import dispatch as dispatch_en
except Exception as e:
    logging.warning(f"EN dispatcher yüklenemedi: {e}")

try:
    from .de import dispatch as dispatch_de
except Exception as e:
    logging.warning(f"DE dispatcher yüklenemedi: {e}")

try:
    from .ar import dispatch as dispatch_ar
except Exception as e:
    logging.warning(f"AR dispatcher yüklenemedi: {e}")