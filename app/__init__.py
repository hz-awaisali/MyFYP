"""Smart University Management System - FastAPI backend."""

__version__ = "1.0.0"

# Patch bcrypt to prevent passlib from raising warnings/errors on newer versions
try:
    import bcrypt
    if not hasattr(bcrypt, "__about__"):
        class MockAbout:
            __version__ = getattr(bcrypt, "__version__", "4.0.0")
        bcrypt.__about__ = MockAbout()
except ImportError:
    pass
