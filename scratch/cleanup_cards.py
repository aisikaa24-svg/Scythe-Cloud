import os

file_path = 'c:/Users/Administrator/Desktop/auto clime/4/extracted_cards.txt'

if os.path.exists(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    cleaned_lines = []
    for line in lines:
        parts = line.strip().split('|')
        if len(parts) >= 3:
            # Normalize Month
            month = parts[1].strip()
            if len(month) == 1: parts[1] = "0" + month
            
            # Normalize Year
            year = parts[2].strip()
            if len(year) == 2:
                parts[2] = "20" + year
            elif len(year) == 1:
                parts[2] = "200" + year # unlikely but safe
                
            # Reconstruct
            cleaned_lines.append("|".join(parts))
        else:
            cleaned_lines.append(line.strip())
            
    # Remove duplicates while we're at it
    unique_lines = list(dict.fromkeys(cleaned_lines))
    
    with open(file_path, 'w') as f:
        for line in unique_lines:
            f.write(line + '\n')
    
    print(f"SUCCESS: Processed {len(lines)} lines. Fixed formatting and removed duplicates.")
else:
    print("File not found.")
