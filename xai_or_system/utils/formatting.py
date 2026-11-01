from typing import List, Optional


def format_currency(value: float, symbol: str = "$") -> str:
    """Format a number as currency."""
    return f"{symbol}{value:,.2f}"


def format_number(value: float, decimals: int = 2) -> str:
    """Format a number with specified decimal places."""
    return f"{value:,.{decimals}f}"


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format a number as a percentage."""
    return f"{value:.{decimals}f}%"


def format_matrix(matrix: List[List[float]], col_width: int = 8) -> str:
    """Format a matrix as a readable string table."""
    if not matrix:
        return "(empty matrix)"
    lines = []
    for row in matrix:
        lines.append("".join(str(val).rjust(col_width) for val in row))
    return "\n".join(lines)


def format_allocation_table(allocation: List[List[float]], cost_matrix: List[List[float]],
                            source_names: Optional[List[str]] = None,
                            dest_names: Optional[List[str]] = None) -> str:
    """Format an allocation table with costs shown as subscripts."""
    rows = len(allocation)
    cols = len(allocation[0]) if rows > 0 else 0
    if source_names is None:
        source_names = [f"S{i+1}" for i in range(rows)]
    if dest_names is None:
        dest_names = [f"D{j+1}" for j in range(cols)]
    lines = []
    header = "       " + "".join(f"{name:>10}" for name in dest_names)
    lines.append(header)
    lines.append("       " + "-" * (10 * cols))
    for i in range(rows):
        row_str = f"{source_names[i]:>5} |"
        for j in range(cols):
            val = allocation[i][j]
            cost = cost_matrix[i][j]
            if val > 0:
                row_str += f"  {int(val):>3}({cost})  "
            else:
                row_str += f"    .     "
        lines.append(row_str)
    return "\n".join(lines)
