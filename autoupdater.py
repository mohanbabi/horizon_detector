import os

def update(update_path):
    # check if path exists
    if not os.path.exists(update_path):
        print('No update directory found. Please check that you have plugged in the thumbdrive.')
        return False
    
    # check if the file is a python file
    updated_files = 0
    for i in os.listdir(update_path):
        if i[-3:] != '.py':
            continue
        
        # do not update the autoupdater file
        if i == 'autoupdater.py':
            continue
        
        # check if the file exists in the current code base
        current_path = '/home/pi/horizon_detector'
        if i not in os.listdir(current_path):
            continue
        
        # check if there have been any updates to the file
        with open(f'{update_path}/{i}') as f:
            text_in_update_file = f.read()
        with open(f'{current_path}/{i}') as f: 
            text_in_current_file = f.read()
        if text_in_update_file == text_in_current_file:
            continue
        
        with open(f'{current_path}/{i}', 'w') as f:
            f.write(text_in_update_file)
            print('Writing...')
        
        updated_files += 1
        
    print(f'{updated_files} files updated.')
    if updated_files > 0:
        return True
    else:
        return False
    
if __name__ == "__main__":
    path = '/media/pi/scratch/update_package'
    files_have_been_updated = update(path)
    print(f'files_have_been_updated: {files_have_been_updated}')
