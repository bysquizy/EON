"""Kullanıcının /hesap komutuyla açıkça çağırdığı güvenli yerel hesaplayıcı."""
import ast
from decimal import Decimal, DivisionByZero, InvalidOperation

class ToolError(ValueError):
    pass

def calculate(expression: str) -> str:
    if len(expression) > 100:
        raise ToolError("İfade çok uzun.")
    try:
        node = ast.parse(expression, mode="eval").body
    except SyntaxError:
        raise ToolError("Geçersiz matematik ifadesi.") from None

    def solve(n, depth=0):
        if depth > 12:
            raise ToolError("İfade çok karmaşık.")
        if isinstance(n, ast.Constant) and type(n.value) in (int, float):
            value = Decimal(str(n.value))
        elif isinstance(n, ast.UnaryOp) and type(n.op) in (ast.UAdd, ast.USub):
            v = solve(n.operand, depth + 1)
            value = v if isinstance(n.op, ast.UAdd) else -v
        elif isinstance(n, ast.BinOp):
            left, right = solve(n.left, depth + 1), solve(n.right, depth + 1)
            op = type(n.op)
            try:
                if op is ast.Add:
                    value = left + right
                elif op is ast.Sub:
                    value = left - right
                elif op is ast.Mult:
                    value = left * right
                elif op is ast.Div:
                    value = left / right
                elif op is ast.Pow and right == right.to_integral_value() and 0 <= right <= 8:
                    value = left ** int(right)
                else:
                    raise ToolError("İşlem desteklenmiyor.")
            except (DivisionByZero, InvalidOperation, OverflowError):
                raise ToolError("Matematik işlemi geçersiz.") from None
        else:
            raise ToolError("Bu komutta yalnızca sayılar ve + - * / ** kullanılabilir.")
        if not value.is_finite() or abs(value) > Decimal("1e20"):
            raise ToolError("Sonuç çok büyük veya geçersiz.")
        return value

    return format(solve(node).normalize(), "f")
