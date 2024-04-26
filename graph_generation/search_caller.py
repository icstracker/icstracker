import sys
from time import time

start = time()

def find_caller(important_func_file, source_file):
    # Read file1 from bottom and find the function
    found = 0
    with open(important_func_file, 'r') as file1:
        lines_file1 = file1.readlines()[::-1]  # Read lines from bottom to top
        for f1 in lines_file1:
            with open(source_file, 'r') as file2:
                lines_file2 = file2.readlines()[::-1]  # Read lines from bottom to top
                for line in lines_file2:
                    if f1 in line:
                        #print(f"Function '{f1}' found in file '{source_file}'")
                        found += 1
                        break
        if found == 0:
            print(f"No calls found from functions in '{important_func_file}' in file '{source_file}'")
        else:
            print(f"Total functions found: {found}")

## Define file paths
#important_func_file = "/home/raihan/CPS-VVI-LOGS-DATA/All-new-logs/10.4.Paper_Table_Format/Table 3/1.HBW_Retrieval/updated_idf_traces_0.005"
#source_file = "/home/raihan/CPS-VVI-LOGS-DATA/All-new-logs/10.2.everything-logged-with-good/hbwall3"
#
## Call the function
#find_caller(important_func_file, source_file)



# Check if the correct number of arguments are provided
if len(sys.argv) != 3:
    print("Usage: python script.py important_func_file_path source_file_path")
    sys.exit(1)

# Extract command-line arguments
important_func_file = sys.argv[1]
source_file = sys.argv[2]
print("Important file path: ", important_func_file)

# Call the function
find_caller(important_func_file, source_file)

end = time()
print(f"Runtime: {(end-start)*1000}")
print()
