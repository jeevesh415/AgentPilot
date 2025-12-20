
import io
import sys

from RestrictedPython import compile_restricted, safe_globals


class SafeIntegratedEnvironment:
    """Safe integrated execution environment using RestrictedPython."""

    def __init__(self, config):
        self.config = config

    def run_code(self, lang: str, code: str, venv_path=None) -> str:
        """Execute Python code in a restricted environment."""
        if lang.lower() != 'python':
            raise ValueError(f"Language '{lang}' is not supported. Only Python is supported.")

        byte_code = compile_restricted(code, '<inline>', 'exec')

        if byte_code.errors:
            return '\n'.join(byte_code.errors)

        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        try:
            exec(byte_code, safe_globals)
            output = sys.stdout.getvalue()
            return output
        finally:
            sys.stdout = old_stdout