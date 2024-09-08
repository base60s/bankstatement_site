import pandas as pd
import os

def merge_excel_files(directory, output_file):
    # Get all .xlsx files in the directory
    excel_files = [f for f in os.listdir(directory) if f.endswith('.xlsx')]
    
    # Create an empty list to store individual dataframes
    dfs = []

    # Read each Excel file and append to the list
    for file in excel_files:
        file_path = os.path.join(directory, file)
        df = pd.read_excel(file_path)
        dfs.append(df)

    # Concatenate all dataframes in the list
    merged_df = pd.concat(dfs, ignore_index=True)

    # Write the merged dataframe to a new Excel file
    merged_df.to_excel(output_file, index=False)
    print(f"Merged file saved as {output_file}")

# Example usage
directory = '/Users/mauriciovelez/Desktop'  # Updated path
output_file = 'merged_file.xlsx'
merge_excel_files(directory, output_file)