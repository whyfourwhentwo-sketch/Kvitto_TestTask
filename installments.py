def build_schedule(amount: int, months: int) -> list[int]:
    base, rem = divmod(amount, months)
    return [base + 1 if i < rem else base for i in range(months)]