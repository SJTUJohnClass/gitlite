# Standard commands and definitions
> init
<<<
D DATE "Date: \w{3} \w{3} \d{2} \d{2}:\d{2}:\d{2} \d{4} [-+]\d{4}"
# A status log header RE.  Captures the commit id in its sole group.
D COMMIT_HEAD "commit ([a-f0-9]{40})\n(?:Merge: [0-9a-f]{7} [0-9a-f]{7}\n)?${DATE}"
# A full log entry.  Captures the entry. Assume logs messages don't contain
# "==="
D COMMIT_LOG "(===\ncommit [a-f0-9]{40}\n(?:Merge: [0-9a-f]{7} [0-9a-f]{7}\n)?${DATE}\n(?:.|\n)*?(?=\Z|\n===))"
# An arbitrary line of text (works even with ?s)
D ARBLINE "[^\n]*(?=\n|\Z)"
# Zero or more arbitrary full lines of text.
D ARBLINES "(?:(?:.|\n)*(?:\n|\Z)|\A|\Z)"
