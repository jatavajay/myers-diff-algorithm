import sys


# ============================================================
# File handling
# ============================================================

def read_file(filename):
    """
    Read a file as raw bytes.

    The assignment requires:
    - split only on byte '\\n'
    - remove the final empty piece caused by a trailing '\\n'
    - preserve '\\r'
    """
    with open(filename, "rb") as file:
        data = file.read()

    lines = data.split(b"\n")

    if lines and lines[-1] == b"":
        lines.pop()

    return lines


# ============================================================
# Linear-space Myers diff
# ============================================================

def find_middle_split(a, alo, ahi, b, blo, bhi):
    """
    Find the middle point of a shortest edit path.

    This is the linear-space Myers "middle snake" search.

    Returns:
        (x, y)
    where the split is:
        a[alo:x]
        b[blo:y]

    The V arrays are discarded after this function returns, so we
    do NOT keep O(D^2) history.
    """

    n = ahi - alo
    m = bhi - blo

    max_d = (n + m + 1) // 2

    offset = max_d
    size = 2 * max_d + 1

    # Forward and reverse frontiers.
    v_forward = [-1] * size
    v_reverse = [-1] * size

    v_forward[offset + 1] = 0
    v_reverse[offset + 1] = 0

    delta = n - m

    # If delta is odd, the forward and reverse paths meet
    # after the forward step.
    front = (delta % 2 != 0)

    forward_start = 0
    forward_end = 0

    reverse_start = 0
    reverse_end = 0

    for d in range(max_d):

        # ----------------------------------------------------
        # Forward search
        # ----------------------------------------------------

        for k in range(
            -d + forward_start,
            d + 1 - forward_end,
            2
        ):
            index = offset + k

            if (
                k == -d
                or (
                    k != d
                    and v_forward[index - 1]
                    < v_forward[index + 1]
                )
            ):
                x = v_forward[index + 1]
            else:
                x = v_forward[index - 1] + 1

            y = x - k

            # Follow the diagonal (snake).
            while (
                x < n
                and y < m
                and a[alo + x] == b[blo + y]
            ):
                x += 1
                y += 1

            v_forward[index] = x

            if x > n:
                forward_end += 2

            elif y > m:
                forward_start += 2

            elif front:
                reverse_index = offset + delta - k

                if (
                    0 <= reverse_index < size
                    and v_reverse[reverse_index] != -1
                ):
                    reverse_x = n - v_reverse[reverse_index]

                    if x >= reverse_x:
                        return x, y

        # ----------------------------------------------------
        # Reverse search
        # ----------------------------------------------------

        for k in range(
            -d + reverse_start,
            d + 1 - reverse_end,
            2
        ):
            index = offset + k

            if (
                k == -d
                or (
                    k != d
                    and v_reverse[index - 1]
                    < v_reverse[index + 1]
                )
            ):
                x = v_reverse[index + 1]
            else:
                x = v_reverse[index - 1] + 1

            y = x - k

            # Follow the diagonal backwards.
            while (
                x < n
                and y < m
                and a[ahi - x - 1] == b[bhi - y - 1]
            ):
                x += 1
                y += 1

            v_reverse[index] = x

            if x > n:
                reverse_end += 2

            elif y > m:
                reverse_start += 2

            elif not front:
                forward_index = offset + delta - k

                if (
                    0 <= forward_index < size
                    and v_forward[forward_index] != -1
                ):
                    forward_x = v_forward[forward_index]

                    # Convert the forward diagonal to y.
                    forward_y = forward_x - (delta - k)

                    # Mirror reverse x into forward coordinates.
                    reverse_x = n - x

                    if forward_x >= reverse_x:
                        return forward_x, forward_y

    return None


def myers_diff(a, b):
    """
    Linear-space Myers diff.

    Returns operations:

        ("keep", start, end)
        ("delete", start, end)
        ("insert", start, end)

    The ranges refer to the original input arrays.

    Auxiliary diff-search space is O(N + M).
    The complete output itself is O(N + M).
    """

    output = []

    # We use an explicit stack rather than Python recursion.
    #
    # This is important for very large files because a recursive
    # implementation could hit Python's recursion limit.
    stack = [
        ("diff", 0, len(a), 0, len(b))
    ]

    while stack:

        task = stack.pop()

        if task[0] == "emit":
            output.append(task[1:])
            continue

        _, alo, ahi, blo, bhi = task

        # ----------------------------------------------------
        # Remove common prefix
        # ----------------------------------------------------

        prefix = 0

        while (
            alo + prefix < ahi
            and blo + prefix < bhi
            and a[alo + prefix] == b[blo + prefix]
        ):
            prefix += 1

        # ----------------------------------------------------
        # Remove common suffix
        # ----------------------------------------------------

        suffix = 0

        while (
            ahi - suffix > alo + prefix
            and bhi - suffix > blo + prefix
            and a[ahi - suffix - 1] == b[bhi - suffix - 1]
        ):
            suffix += 1

        # Stack is LIFO.
        # Push suffix first so it is emitted after the middle.
        if suffix:
            stack.append(
                ("emit", "keep", ahi - suffix, ahi)
            )

        middle_a_start = alo + prefix
        middle_a_end = ahi - suffix

        middle_b_start = blo + prefix
        middle_b_end = bhi - suffix

        # ----------------------------------------------------
        # Solve middle problem
        # ----------------------------------------------------

        if (
            middle_a_start < middle_a_end
            or middle_b_start < middle_b_end
        ):

            # A is empty -> insertion only.
            if middle_a_start == middle_a_end:

                stack.append(
                    (
                        "emit",
                        "insert",
                        middle_b_start,
                        middle_b_end,
                    )
                )

            # B is empty -> deletion only.
            elif middle_b_start == middle_b_end:

                stack.append(
                    (
                        "emit",
                        "delete",
                        middle_a_start,
                        middle_a_end,
                    )
                )

            # ------------------------------------------------
            # One element on A
            # ------------------------------------------------

            elif middle_a_end - middle_a_start == 1:

                value = a[middle_a_start]

                found = None

                for j in range(
                    middle_b_start,
                    middle_b_end
                ):
                    if b[j] == value:
                        found = j
                        break

                if found is None:

                    # No common element:
                    # delete first, then insert.
                    stack.append(
                        (
                            "emit",
                            "insert",
                            middle_b_start,
                            middle_b_end,
                        )
                    )

                    stack.append(
                        (
                            "emit",
                            "delete",
                            middle_a_start,
                            middle_a_end,
                        )
                    )

                else:

                    # Desired order:
                    #
                    # insert-before
                    # keep
                    # insert-after
                    #
                    # Push in reverse because stack is LIFO.

                    stack.append(
                        (
                            "emit",
                            "insert",
                            found + 1,
                            middle_b_end,
                        )
                    )

                    stack.append(
                        (
                            "emit",
                            "keep",
                            middle_a_start,
                            middle_a_start + 1,
                        )
                    )

                    stack.append(
                        (
                            "emit",
                            "insert",
                            middle_b_start,
                            found,
                        )
                    )

            # ------------------------------------------------
            # One element on B
            # ------------------------------------------------

            elif middle_b_end - middle_b_start == 1:

                value = b[middle_b_start]

                found = None

                for i in range(
                    middle_a_start,
                    middle_a_end
                ):
                    if a[i] == value:
                        found = i
                        break

                if found is None:

                    stack.append(
                        (
                            "emit",
                            "insert",
                            middle_b_start,
                            middle_b_end,
                        )
                    )

                    stack.append(
                        (
                            "emit",
                            "delete",
                            middle_a_start,
                            middle_a_end,
                        )
                    )

                else:

                    # Desired order:
                    #
                    # delete-before
                    # keep
                    # delete-after
                    #
                    # Push in reverse.

                    stack.append(
                        (
                            "emit",
                            "delete",
                            found + 1,
                            middle_a_end,
                        )
                    )

                    stack.append(
                        (
                            "emit",
                            "keep",
                            found,
                            found + 1,
                        )
                    )

                    stack.append(
                        (
                            "emit",
                            "delete",
                            middle_a_start,
                            found,
                        )
                    )

            else:

                split = find_middle_split(
                    a,
                    middle_a_start,
                    middle_a_end,
                    b,
                    middle_b_start,
                    middle_b_end,
                )

                # This should only occur when there is no
                # useful split. In that case all A is deleted
                # and all B is inserted.
                if split is None:

                    stack.append(
                        (
                            "emit",
                            "insert",
                            middle_b_start,
                            middle_b_end,
                        )
                    )

                    stack.append(
                        (
                            "emit",
                            "delete",
                            middle_a_start,
                            middle_a_end,
                        )
                    )

                else:

                    split_x, split_y = split

                    a_mid_len = middle_a_end - middle_a_start
                    b_mid_len = middle_b_end - middle_b_start

                    # Safety against a zero-progress split.
                    if (
                        split_x == 0
                        and split_y == 0
                    ) or (
                        split_x == a_mid_len
                        and split_y == b_mid_len
                    ):

                        stack.append(
                            (
                                "emit",
                                "insert",
                                middle_b_start,
                                middle_b_end,
                            )
                        )

                        stack.append(
                            (
                                "emit",
                                "delete",
                                middle_a_start,
                                middle_a_end,
                            )
                        )

                    else:

                        # Right half is pushed first.
                        # Left half is therefore processed first.

                        stack.append(
                            (
                                "diff",
                                middle_a_start + split_x,
                                middle_a_end,
                                middle_b_start + split_y,
                                middle_b_end,
                            )
                        )

                        stack.append(
                            (
                                "diff",
                                middle_a_start,
                                middle_a_start + split_x,
                                middle_b_start,
                                middle_b_start + split_y,
                            )
                        )

        # ----------------------------------------------------
        # Prefix is processed first.
        # ----------------------------------------------------

        if prefix:
            stack.append(
                (
                    "emit",
                    "keep",
                    alo,
                    alo + prefix,
                )
            )

    return output


# ============================================================
# Delete-before-insert ordering
# ============================================================

def apply_delete_first_rule(operations):
    """
    Reorder every change block so that deletions come before
    insertions.

    A change block ends whenever a keep operation appears.
    """

    result = []

    i = 0

    while i < len(operations):

        operation = operations[i]

        if operation[0] == "keep":
            result.append(operation)
            i += 1
            continue

        deletions = []
        insertions = []

        while (
            i < len(operations)
            and operations[i][0] != "keep"
        ):

            operation = operations[i]

            if operation[0] == "delete":
                deletions.append(operation)
            else:
                insertions.append(operation)

            i += 1

        result.extend(deletions)
        result.extend(insertions)

    return result


# ============================================================
# Part A
# ============================================================

def print_lines_diff(a, b):
    """
    Print the minimal line diff.
    """

    operations = myers_diff(a, b)

    operations = apply_delete_first_rule(
        operations
    )

    stdout = sys.stdout.buffer

    for operation in operations:

        kind, start, end = operation

        if kind == "keep":

            for i in range(start, end):
                stdout.write(b" " + a[i] + b"\n")

        elif kind == "delete":

            for i in range(start, end):
                stdout.write(b"-" + a[i] + b"\n")

        else:

            for i in range(start, end):
                stdout.write(b"+" + b[i] + b"\n")


# ============================================================
# Character highlighting
# ============================================================

def merge_ranges(ranges):
    """
    Merge overlapping or touching half-open ranges.
    """

    if not ranges:
        return []

    ranges.sort()

    merged = [
        [ranges[0][0], ranges[0][1]]
    ]

    for start, end in ranges[1:]:

        last = merged[-1]

        if start <= last[1]:

            if end > last[1]:
                last[1] = end

        else:

            merged.append([start, end])

    return [
        (start, end)
        for start, end in merged
    ]


def get_changed_ranges(old_line, new_line):
    """
    Find the minimum character changes between two lines.

    Python strings iterate over Unicode code points, which is
    exactly what Part B requires.
    """

    old_chars = list(old_line)
    new_chars = list(new_line)

    operations = myers_diff(
        old_chars,
        new_chars
    )

    old_ranges = []
    new_ranges = []

    old_pos = 0
    new_pos = 0

    for operation in operations:

        kind, start, end = operation

        length = end - start

        if kind == "keep":

            old_pos += length
            new_pos += length

        elif kind == "delete":

            old_ranges.append(
                (old_pos, old_pos + length)
            )

            old_pos += length

        else:

            new_ranges.append(
                (new_pos, new_pos + length)
            )

            new_pos += length

    return (
        merge_ranges(old_ranges),
        merge_ranges(new_ranges),
    )


def format_ranges(ranges):
    """
    Convert ranges to:
        3-5,9-12
    or:
        .
    """

    if not ranges:
        return "."

    return ",".join(
        f"{start}-{end}"
        for start, end in ranges
    )


# ============================================================
# Part B
# ============================================================

def print_highlight(a, b):
    """
    Print Part A plus character-level highlight lines.

    Lines in a change block are paired individually:
        1st deletion <-> 1st insertion
        2nd deletion <-> 2nd insertion
        ...

    A '?' line is printed immediately after each paired '+' line.
    """

    operations = myers_diff(a, b)
    operations = apply_delete_first_rule(operations)

    stdout = sys.stdout.buffer

    i = 0

    while i < len(operations):

        operation = operations[i]

        # ----------------------------------------------------
        # Keep block
        # ----------------------------------------------------

        if operation[0] == "keep":

            _, start, end = operation

            for index in range(start, end):
                stdout.write(
                    b" " + a[index] + b"\n"
                )

            i += 1
            continue

        # ----------------------------------------------------
        # Collect one complete change block
        # ----------------------------------------------------

        deleted_lines = []
        inserted_lines = []

        while (
            i < len(operations)
            and operations[i][0] != "keep"
        ):

            kind, start, end = operations[i]

            if kind == "delete":

                for index in range(start, end):
                    deleted_lines.append(index)

            elif kind == "insert":

                for index in range(start, end):
                    inserted_lines.append(index)

            i += 1

        # ----------------------------------------------------
        # Print ALL deletions first
        # ----------------------------------------------------

        for index in deleted_lines:
            stdout.write(
                b"-" + a[index] + b"\n"
            )

        # ----------------------------------------------------
        # Pair individual deleted/inserted lines
        # ----------------------------------------------------

        pair_count = min(
            len(deleted_lines),
            len(inserted_lines),
        )

        for pair_index in range(pair_count):

            old_index = deleted_lines[pair_index]
            new_index = inserted_lines[pair_index]

            # Print the inserted line.
            stdout.write(
                b"+" + b[new_index] + b"\n"
            )

            # Calculate character-level changes.
            old_line = a[old_index].decode("utf-8")
            new_line = b[new_index].decode("utf-8")

            old_ranges, new_ranges = get_changed_ranges(
                old_line,
                new_line,
            )

            highlight = (
                "? "
                + format_ranges(old_ranges)
                + " | "
                + format_ranges(new_ranges)
                + "\n"
            )

            stdout.write(
                highlight.encode("utf-8")
            )

        # ----------------------------------------------------
        # Remaining unpaired insertions
        # ----------------------------------------------------

        for pair_index in range(
            pair_count,
            len(inserted_lines),
        ):

            new_index = inserted_lines[pair_index]

            stdout.write(
                b"+" + b[new_index] + b"\n"
            )

# ============================================================
# Main
# ============================================================

def main():
    if len(sys.argv) != 4:
        return 2

    command = sys.argv[1]
    file_a = sys.argv[2]
    file_b = sys.argv[3]

    if command not in ("lines", "highlight"):
        return 2

    try:
        a = read_file(file_a)
        b = read_file(file_b)

    except (OSError, IOError) as error:
        print(
            f"error: {error}",
            file=sys.stderr,
        )
        return 2

    if command == "lines":
        print_lines_diff(a, b)

    else:
        print_highlight(a, b)

    return 0


if __name__ == "__main__":
    sys.exit(main())