import argparse
import os
import shutil


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i","--input",required= True, type=str,help="Folder containing the full video sequence")
    parser.add_argument("-o", "--out_dir", required= True, type=str,help="Output folder")
    parser.add_argument("-s","--start", required=True, type=int, help="first frame id")
    parser.add_argument("-st", "--stop", required=True, type=int, help="last frame id")
    parser.add_argument("--step", required=False, type=int, default=1, help="frame step size, every 'step'th frame will be copied to the output folder")
    return parser.parse_args()


def get_id(filename:str):
    return filename.split(".")[0].split("_")[1]


if __name__ == "__main__":
    args = parse_args()
    in_dir = args.input
    out_dir = args.out_dir
    valid_idxs = list(range(args.start,args.stop,args.step))
    os.makedirs(out_dir, exist_ok=True)
    for file in os.listdir(in_dir):
        id = get_id(file)
        if int(get_id(file)) in valid_idxs:
            shutil.copy(os.path.join(in_dir,file),f'{os.path.join(out_dir,id)}.jpg')
