from typing import List, Tuple, Optional


def validate_numeric_matrix(matrix: List[List[float]], name: str = "Matrix") -> Tuple[bool, Optional[str]]:
    """Validate that a 2D list contains only numeric values."""
    if not matrix or not isinstance(matrix, list):
        return False, f"{name} must be a non-empty list."
    for i, row in enumerate(matrix):
        if not isinstance(row, list):
            return False, f"{name} row {i} must be a list."
        for j, val in enumerate(row):
            if not isinstance(val, (int, float)):
                return False, f"{name}[{i}][{j}] = '{val}' is not numeric."
    return True, None


def validate_numeric_vector(vector: List[float], name: str = "Vector") -> Tuple[bool, Optional[str]]:
    """Validate that a list contains only numeric values."""
    if not vector or not isinstance(vector, list):
        return False, f"{name} must be a non-empty list."
    for i, val in enumerate(vector):
        if not isinstance(val, (int, float)):
            return False, f"{name}[{i}] = '{val}' is not numeric."
    return True, None


def validate_positive_vector(vector: List[float], name: str = "Vector") -> Tuple[bool, Optional[str]]:
    """Validate that all values in a vector are positive."""
    valid, err = validate_numeric_vector(vector, name)
    if not valid:
        return valid, err
    for i, val in enumerate(vector):
        if val <= 0:
            return False, f"{name}[{i}] = {val} must be positive."
    return True, None


def validate_non_negative_matrix(matrix: List[List[float]], name: str = "Matrix") -> Tuple[bool, Optional[str]]:
    """Validate that all values in a matrix are non-negative."""
    valid, err = validate_numeric_matrix(matrix, name)
    if not valid:
        return valid, err
    for i, row in enumerate(matrix):
        for j, val in enumerate(row):
            if val < 0:
                return False, f"{name}[{i}][{j}] = {val} must be non-negative."
    return True, None


def validate_non_negative_vector(vector: List[float], name: str = "Vector") -> Tuple[bool, Optional[str]]:
    """Validate that all values in a vector are non-negative."""
    valid, err = validate_numeric_vector(vector, name)
    if not valid:
        return valid, err
    for i, val in enumerate(vector):
        if val < 0:
            return False, f"{name}[{i}] = {val} must be non-negative."
    return True, None


def validate_matrix_dimensions(matrix: List[List[float]], expected_rows: int, expected_cols: int,
                                name: str = "Matrix") -> Tuple[bool, Optional[str]]:
    """Validate that a matrix has the expected dimensions."""
    if len(matrix) != expected_rows:
        return False, f"{name} has {len(matrix)} rows, expected {expected_rows}."
    for i, row in enumerate(matrix):
        if len(row) != expected_cols:
            return False, f"{name} row {i} has {len(row)} columns, expected {expected_cols}."
    return True, None


def validate_square_matrix(matrix: List[List[float]], name: str = "Matrix") -> Tuple[bool, Optional[str]]:
    """Validate that a matrix is square."""
    if not matrix:
        return False, f"{name} must be non-empty."
    n = len(matrix)
    for i, row in enumerate(matrix):
        if len(row) != n:
            return False, f"{name} is not square: row {i} has {len(row)} columns, expected {n}."
    return True, None
