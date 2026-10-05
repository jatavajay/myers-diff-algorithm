import sys


# ============================================================
# 1. Read file
# ============================================================

def read_file(filename):
    """
    Read a file as raw bytes and return its lines.

    Rules:
    - Split on \\n
    - Remove empty piece caused by final \\n
    - Keep \\r as part of the line
    """

    with open(filename, "rb") as file:
        data = file.read()

    lines = data.split(b"\n")

    # A final newline does not create an extra line.
    if lines and lines[-1] == b"":
        lines.pop()

    return lines


# ============================================================
# 2. Myers Diff
# ============================================================

def myers_diff(a, b):
    """
    Find the shortest edit path between two sequences.

    This function works for both:
        - lines   -> Part A
        - chars   -> Part B

    a = old sequence
    b = new sequence
    """

    n = len(a)
    m = len(b)

    max_d = n + m

    # V[k] = furthest x reached on diagonal k
    v = {1: 0}

    # Save V for every D for backtracking.
    history = []

    # D = number of insertions + deletions
    for d in range(max_d + 1):

        for k in range(-d, d + 1, 2):

            # ------------------------------------------------
            # Decide where this path comes from.
            # ------------------------------------------------

            if k == -d:
                # Come from k + 1
                x = v[k + 1]

            elif k == d:
                # Come from k - 1
                x = v[k - 1] + 1

            elif v[k - 1] < v[k + 1]:
                # Insertion
                x = v[k + 1]

            else:
                # Deletion
                x = v[k - 1] + 1

            # k = x - y
            y = x - k

            # ------------------------------------------------
            # Snake:
            # move through equal elements.
            # ------------------------------------------------

            while (
                x < n
                and y < m
                and a[x] == b[y]
            ):
                x += 1
                y += 1

            # Save furthest x on this diagonal.
            v[k] = x

            # ------------------------------------------------
            # Have we reached the end?
            # ------------------------------------------------

            if x >= n and y >= m:

                history.append(v.copy())

                return history, d

        # Save this D level.
        history.append(v.copy())

    return history, max_d


# ============================================================
# 3. Build Diff
# ============================================================

def build_diff(a, b, history):
    """
    Reconstruct the edit script using the saved V arrays.

    Returns:

        (" ", item) -> keep
        ("-", item) -> delete
        ("+", item) -> insert
    """

    x = len(a)
    y = len(b)

    result = []

    # --------------------------------------------------------
    # Backtrack from the end.
    # --------------------------------------------------------

    for d in range(len(history) - 1, 0, -1):

        previous_v = history[d - 1]

        # Current diagonal
        k = x - y

        # ----------------------------------------------------
        # Find previous diagonal.
        # ----------------------------------------------------

        if (
            k == -d
            or (
                k != d
                and previous_v.get(k - 1, -1)
                < previous_v.get(k + 1, -1)
            )
        ):
            previous_k = k + 1

        else:
            previous_k = k - 1

        previous_x = previous_v[previous_k]
        previous_y = previous_x - previous_k

        # ----------------------------------------------------
        # Matching elements = snake.
        # ----------------------------------------------------

        while (
            x > previous_x
            and y > previous_y
        ):

            result.append(
                (" ", a[x - 1])
            )

            x -= 1
            y -= 1

        # ----------------------------------------------------
        # Actual edit.
        # ----------------------------------------------------

        if x == previous_x:

            # Insert from B.
            result.append(
                ("+", b[y - 1])
            )

            y -= 1

        else:

            # Delete from A.
            result.append(
                ("-", a[x - 1])
            )

            x -= 1

    # --------------------------------------------------------
    # Remaining beginning portion.
    # --------------------------------------------------------

    while x > 0 and y > 0:

        result.append(
            (" ", a[x - 1])
        )

        x -= 1
        y -= 1

    while x > 0:

        result.append(
            ("-", a[x - 1])
        )

        x -= 1

    while y > 0:

        result.append(
            ("+", b[y - 1])
        )

        y -= 1

    # We built it backwards.
    result.reverse()

    return result


# ============================================================
# 4. Delete-first rule
# ============================================================

def apply_delete_first_rule(result):
    """
    Inside every change block:

        - lines come first
        + lines come second

    Example:

        -old
        +new
    """

    final_result = []

    deletions = []
    insertions = []

    for symbol, line in result:

        if symbol == " ":

            # End current change block.

            final_result.extend(deletions)
            final_result.extend(insertions)

            deletions = []
            insertions = []

            final_result.append(
                (" ", line)
            )

        elif symbol == "-":

            deletions.append(
                ("-", line)
            )

        else:

            insertions.append(
                ("+", line)
            )

    # Flush last change block.
    final_result.extend(deletions)
    final_result.extend(insertions)

    return final_result


# ============================================================
# 5. Convert changed positions to ranges
# ============================================================

def make_ranges(positions):
    """
    Convert character positions into half-open ranges.

    Example:

        [3, 4, 5, 9, 10]

    becomes:

        3-6,9-11
    """

    if not positions:
        return "."

    ranges = []

    start = positions[0]
    previous = positions[0]

    for position in positions[1:]:

        # Consecutive positions belong to one range.
        if position == previous + 1:

            previous = position

        else:

            ranges.append(
                f"{start}-{previous + 1}"
            )

            start = position
            previous = position

    # Add final range.
    ranges.append(
        f"{start}-{previous + 1}"
    )

    return ",".join(ranges)


# ============================================================
# 6. Find changed character ranges
# ============================================================

def get_changed_ranges(old_line, new_line):
    """
    Find which characters changed between two lines.

    Python strings use Unicode code points, so:

        😀 = one character

    as required by the assignment.

    Returns:

        old_ranges, new_ranges
    """

    # Convert each line into Unicode code points.
    old_chars = list(old_line)
    new_chars = list(new_line)

    # Run Myers again, this time on characters.
    history, edit_count = myers_diff(
        old_chars,
        new_chars
    )

    char_diff = build_diff(
        old_chars,
        new_chars,
        history
    )

    char_diff = apply_delete_first_rule(
        char_diff
    )

    old_positions = []
    new_positions = []

    old_index = 0
    new_index = 0

    # --------------------------------------------------------
    # Walk through character diff.
    # --------------------------------------------------------

    for symbol, char in char_diff:

        if symbol == " ":

            # Same character on both sides.
            old_index += 1
            new_index += 1

        elif symbol == "-":

            # Character removed from old line.
            old_positions.append(
                old_index
            )

            old_index += 1

        else:

            # Character inserted into new line.
            new_positions.append(
                new_index
            )

            new_index += 1

    old_ranges = make_ranges(
        old_positions
    )

    new_ranges = make_ranges(
        new_positions
    )

    return old_ranges, new_ranges


# ============================================================
# 7. Print Part A + Part B
# ============================================================

def print_highlight(result):
    """
    Print the normal line diff.

    Additionally, for each paired -/+ line:

        ? old_ranges | new_ranges

    is printed immediately after the + line.
    """

    output = sys.stdout.buffer

    i = 0

    while i < len(result):

        symbol, line = result[i]

        # ----------------------------------------------------
        # Keep line
        # ----------------------------------------------------

        if symbol == " ":

            output.write(
                b" " + line + b"\n"
            )

            i += 1
            continue

        # ----------------------------------------------------
        # We are inside a change block.
        # ----------------------------------------------------

        deletions = []
        insertions = []

        # Collect the entire change block.
        while (
            i < len(result)
            and result[i][0] != " "
        ):

            symbol, line = result[i]

            if symbol == "-":

                deletions.append(line)

            else:

                insertions.append(line)

            i += 1

        # ----------------------------------------------------
        # Print all deletions first.
        # ----------------------------------------------------

        for line in deletions:

            output.write(
                b"-" + line + b"\n"
            )

        # ----------------------------------------------------
        # Print insertions.
        #
        # Pair:
        #
        # deletion[0] <-> insertion[0]
        # deletion[1] <-> insertion[1]
        # ...
        # ----------------------------------------------------

        for index, new_line in enumerate(insertions):

            output.write(
                b"+" + new_line + b"\n"
            )

            # Only paired lines get a ? line.
            if index < len(deletions):

                old_line = deletions[index]

                # Highlight inputs are guaranteed valid UTF-8.
                old_text = old_line.decode(
                    "utf-8"
                )

                new_text = new_line.decode(
                    "utf-8"
                )

                old_ranges, new_ranges = (
                    get_changed_ranges(
                        old_text,
                        new_text
                    )
                )

                highlight_line = (
                    f"? {old_ranges} | {new_ranges}\n"
                )

                output.write(
                    highlight_line.encode("ascii")
                )


# ============================================================
# 8. Main
# ============================================================

def main():

    # --------------------------------------------------------
    # Expected:
    #
    # python src/main.py highlight A B
    # --------------------------------------------------------

    if (
        len(sys.argv) != 4
        or sys.argv[1] not in ("lines", "highlight")
    ):

        print(
            "Usage: python src/main.py lines A B",
            file=sys.stderr
        )

        print(
            "   or: python src/main.py highlight A B",
            file=sys.stderr
        )

        return 2

    command = sys.argv[1]

    old_filename = sys.argv[2]
    new_filename = sys.argv[3]

    # --------------------------------------------------------
    # Read both files before producing any stdout.
    # --------------------------------------------------------

    try:

        old_file = read_file(
            old_filename
        )

        new_file = read_file(
            new_filename
        )

    except OSError as error:

        print(
            f"Error: {error}",
            file=sys.stderr
        )

        return 2

    # --------------------------------------------------------
    # Part A: line-level Myers diff.
    # --------------------------------------------------------

    history, edit_count = myers_diff(
        old_file,
        new_file
    )

    result = build_diff(
        old_file,
        new_file,
        history
    )

    # Apply delete-first rule.
    result = apply_delete_first_rule(
        result
    )

    # --------------------------------------------------------
    # Choose command.
    # --------------------------------------------------------

    if command == "lines":

        # Part A only.
        # Print only the diff.
        for symbol, line in result:

            sys.stdout.buffer.write(
                symbol.encode("ascii")
                + line
                + b"\n"
            )

    else:

        # Part B:
        # Part A + character highlights.
        print_highlight(result)

    return 0


# ============================================================
# Start program
# ============================================================

if __name__ == "__main__":
    sys.exit(main())