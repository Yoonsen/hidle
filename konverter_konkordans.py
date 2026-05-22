import csv
import re

input_file = "konkordans-kysten.txt"
output_file = "konkordans-kysten.csv"

rows = []

current_aar = None
current_meta = None
current_avsender = None
current_uid = None

with open(input_file, encoding="utf-8") as f:
    for line in f:
        line = line.rstrip("\n")

        section_match = re.match(r"===\s+(.+?)\.txt\s+\(\d+ treff\)\s+===", line)
        if section_match:
            filename = section_match.group(1)
            no_uid_match = re.search(r"(no-uid_[a-f0-9]+)$", filename)
            uuid_match = re.search(r"([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})$", filename)
            if no_uid_match:
                current_uid = no_uid_match.group(1)
            elif uuid_match:
                current_uid = uuid_match.group(1)
            else:
                current_uid = None
            continue

        meta_match = re.match(r"Aar:\s*(.+?)\s*\|\s*Avsender:\s*(.+)", line)
        if meta_match:
            current_aar = meta_match.group(1).strip()
            current_avsender = meta_match.group(2).strip()
            current_meta = line.strip()
            if current_uid:
                current_meta = f"{current_meta} | {current_uid}"
            continue

        if line.startswith("- "):
            konkordans = line[2:].strip()
            rows.append({
                "aar": current_aar,
                "metadata": current_meta,
                "avsender": current_avsender,
                "konkordanse": konkordans,
            })

with open(output_file, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["aar", "metadata", "avsender", "konkordanse"])
    writer.writeheader()
    writer.writerows(rows)

print(f"Ferdig: {len(rows)} rader skrevet til {output_file}")
