# -*- coding = utf-8 -*-
# @Time: 2020/4/7 11:36
# @Author: zhanyu Wang
# @File: get_roco.py
# @Software: PyCharm

""" Download packages and extract images based on dlinks.txt files. """

import argparse
import multiprocessing
import os
import tempfile
import requests
import tarfile
import shutil
import threading
from tqdm import tqdm
import json
import time
tempfile.gettempdir()

DLINKS_FOLDERS = [
    'data_roco/test/radiology',
    'data_roco/test/non-radiology',
    'data_roco/train/radiology',
    'data_roco/train/non-radiology',
    'data_roco/validation/radiology',
    'data_roco/validation/non-radiology',
]


def log_status(index, pmc_id, num_groups, dtime):
    print("{:.3%}".format(1. * index / num_groups) + ' | '
          + str(index) + '/' + str(num_groups) + ' | '
          + 'time:{:.4f}s'.format(dtime) + ' | ' + pmc_id)


def extract_image_info(line, image_dir):
    line_parts_tab = line.split("\t")
    change_name = line_parts_tab[0].strip() + ".jpg"
    image_name = line_parts_tab[-1].strip()
    archive_url = line_parts_tab[1].split(' ')[2]
    pmc_id = archive_url.split(os.sep)[-1][:-7]
    image_dir = os.path.join(image_dir, "images")
    return change_name, archive_url, image_name, image_dir


def collect_dlinks_lines(dataset_dir):
    lines_folder = []
    for folder in DLINKS_FOLDERS:
        lines = []
        filename = os.path.join(dataset_dir, folder, 'dlinks.txt')
        image_dir = os.path.join(os.path.dirname(filename), args.subdir)
        if not os.path.exists(image_dir):
            os.mkdir(image_dir, 0o755)

        with open(filename) as dlinks_file:
            lines.extend([[line.rstrip('\n'), folder] for line in dlinks_file])
        lines_folder.append(lines)
    return lines_folder


def group_lines_by_archive(lines_folder):
    groups_folder = []
    for lines in lines_folder:
        groups = []
        for line, folder in lines:
            image_info = extract_image_info(line, folder)
            groups.append(image_info)
        groups_folder.append(groups)
    return groups_folder


def process_group(group, missed_images):
    downloaded = True
    dataset_dir = args.dataset_dir
    extraction_dir_name = args.extraction_dir

    new_image_name = group[0]
    archive_url = "ht" + group[1][1:]
    image_name = group[2]
    new_image_savepath = group[3]

    archive_filename = os.path.join(extraction_dir_name,
                                    archive_url.split('/')[-1])

    if not os.path.isdir(archive_filename[:-7]):
        # 下载文件
        file = requests.get(archive_url)
        if file:
            with open(archive_filename, "wb") as f:
                f.write(file.content)
            # 解压文件到其文件夹
            t = tarfile.open(archive_filename)
            t.extractall(extraction_dir_name)
            t.close()
            os.remove(archive_filename)
            print("del {}".format(archive_filename))
        else:
            missed_images.append(new_image_name)
            downloaded = False
    else:
        print("\nexisted:{}".format(archive_filename))

    # 复制文件到相应的新文件夹
    if downloaded:
        try:
            image_path = os.path.join(archive_filename[:-7], image_name)
            new_image_path = os.path.join(dataset_dir, new_image_savepath, new_image_name)
            shutil.copy(image_path, new_image_path)
        except FileNotFoundError as e:
            print(e)
            missed_images.append(new_image_name)
    else:
        new_image_path = 'Download Failed'
    # print(new_image_path)
    return new_image_path


def parse_args():
    parser = argparse.ArgumentParser(
        description=__doc__.strip(),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        '-s', '--subdir',
        help='name of image subdirectory, relative to dlinks.txt location',
        default='images'
    )

    parser.add_argument(
        '-e', '--extraction-dir',
        help='path to the extraction directory where downloaded archives and '
             + 'images are stored',
        default=os.path.join(r"D:\roco_source", 'roco-dataset'),
    )

    parser.add_argument(
        '--dataset_dir',
        type=str,
        default=r"./",
    )

    parser.add_argument(
        '--output_json',
        type=str,
        default=r"download_info.json",
        help='saving the progress of current downloading',
    )

    return parser.parse_args()


def run(groups, downloading_infos):
    num_groups = len(groups)
    # for i, group in enumerate(groups):
    #     pmc_id = process_group(group)
    #     log_status(i, pmc_id, num_groups)
    try:
        tag = groups[0][3].split("\\")[0].split('/')
        tag = "{}-{}".format(tag[1], tag[2])
        print('********Now is downloading {}*********'.format(tag))
        for i, group in enumerate(groups):
            pmc_id = process_group(group)
            log_status(i, pmc_id, num_groups)
            downloading_infos[tag] = i
    except (RuntimeError, KeyboardInterrupt):
        json.dump(downloading_infos, open(args.output_json, 'w'))
        print('json saved')

if __name__ == '__main__':
    continue_download = False
    args = parse_args()
    print('Fetching ROCO dataset images...')
    lines_folder = collect_dlinks_lines(args.dataset_dir)
    groups_folder = group_lines_by_archive(lines_folder)
    num_groups = len(groups_folder)

    ## 多线程下载
    # downloading_infos = {}
    # threads = []
    # for groups in groups_folder:
    #     t1 = threading.Thread(target=run, args=(groups, downloading_infos,))
    #     threads.append(t1)
    #
    # for i, thread in enumerate(threads):
    #     thread.start()
    #     print("thread {} started".format(i))
    #
    # for thread in threads:
    #     thread.join()

    # 单线程下载
    if continue_download:
        missed_images = json.load(open('./missed_images.json', 'r'))
        downloading_infos = json.load(open('./download_info.json', 'r'))
        print(downloading_infos)
    else:
        downloading_infos = {}
        missed_images = []

    try:
        for i, groups in enumerate(groups_folder):
            num_groups = len(groups)
            tag = groups[0][3].split("\\")[0].split('/')
            tag = "{}-{}".format(tag[1], tag[2])
            if tag in downloading_infos:
                counter = downloading_infos[tag]
            else:
                counter = 0
            print('********Now is downloading {}*********'.format(tag))
            for i, group in enumerate(groups):
                if i < counter:
                    continue
                start_time = time.time()
                pmc_id = process_group(group, missed_images)
                end_time = time.time()
                log_status(i, pmc_id, num_groups, end_time-start_time)
                downloading_infos[tag] = i
            print('finished {}'.format(tag))
            json.dump(downloading_infos, open(args.output_json, 'w'))
            json.dump(missed_images, open('missed_images.json', 'w'))

    except Exception as e:
        print(e)
        json.dump(downloading_infos, open(args.output_json, 'w'))
        json.dump(missed_images, open('missed_images.json', 'w'))