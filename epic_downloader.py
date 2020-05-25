import argparse
import os
import csv
import shutil
import sys

try:
    import urllib.request
    import urllib.error
    from pathlib import Path
except ImportError as e:
    print('Error: {}'.format(e))
    print('This script works with Python 3.5+. Please use a more recent version of Python')
    exit(-1)


def print_header(header, char='*'):
    print()
    print(char * len(header))
    print(header)
    print(char * len(header))
    print()


class EpicDownloader:
    def __init__(self,
                 epic_55_base_url='https://data.bris.ac.uk/datasets/3h91syskeag572hl6tvuovwv4d',
                 epic_100_base_url='https://data.bris.ac.uk/datasets/2g1n6qdydwa9u22shpxqzp0t8m',
                 base_output=str(Path.home()),
                 splits_path_epic_55='data/epic_55_splits.csv',
                 splits_path_epic_100='data/epic_100_splits.csv'):
        self.base_url_55 = epic_55_base_url.rstrip('/')
        self.base_url_100 = epic_100_base_url.rstrip('/')
        self.base_output = os.path.join(base_output, 'EPIC-KITCHENS')
        self.videos_per_split = {}
        self.challenges_splits = []
        self.parse_splits(splits_path_epic_55, splits_path_epic_100)

    @staticmethod
    def download_file(url, output_path):
        Path(os.path.dirname(output_path)).mkdir(parents=True, exist_ok=True)

        try:
            with urllib.request.urlopen(url) as response, open(output_path, 'wb') as output_file:
                print('Downloading\nfrom  {}\nto    {}'.format(url, output_path))
                shutil.copyfileobj(response, output_file)
        except urllib.error.HTTPError as e:
            print('Could not download file from {}\nError: {}'.format(url, str(e)))

    @staticmethod
    def parse_bool(b):
        return b.lower().strip() in ['true', 'yes', 'y']

    def parse_splits(self, epic_55_splits_path, epic_100_splits_path):
        epic_55_videos = {}

        with open(epic_55_splits_path) as csvfile:
            reader = csv.DictReader(csvfile, delimiter=',')

            for row in reader:
                epic_55_videos[row['video_id']] = row['split']

        with open(epic_100_splits_path) as csvfile:
            reader = csv.DictReader(csvfile, delimiter=',')
            self.challenges_splits = [f for f in reader.fieldnames if f != 'video_id']

            for f in self.challenges_splits:
                self.videos_per_split[f] = []

            for row in reader:
                video_id = row['video_id']
                parts = video_id.split('_')
                participant = int(parts[0].split('P')[1])
                extension = len(parts[1]) == 3
                epic_55_split = None if extension else epic_55_videos[video_id]
                v = {'video_id': video_id, 'participant': participant, 'participant_str': parts[0],
                     'extension': extension, 'epic_55_split': epic_55_split}

                for split in self.challenges_splits:
                    if self.parse_bool(row[split]):
                        self.videos_per_split[split].append(v)

    def download_consent_forms(self, video_dicts):
        files_55 = ['ConsentForm.pdf', 'ParticipantsInformationSheet.pdf']

        for f in files_55:
            output_path = os.path.join(self.base_output, 'ConsentForms', 'EPIC-55-{}'.format(f))
            url = '/'.join([self.base_url_55, 'ConsentForms', f])
            self.download_file(url, output_path)

        output_path = os.path.join(self.base_output, 'ConsentForms', 'EPIC-100-ConsentForm.pdf')
        url = '/'.join([self.base_url_100, 'ConsentForms', 'consent-form.pdf'])
        self.download_file(url, output_path)

    def download_videos(self, video_dicts, file_ext='MP4'):
        def epic_55_parts(d):
            return ['videos', d['epic_55_split'], d['participant_str'], '{}.{}'.format(d['video_id'], file_ext)]

        def epic_100_parts(d):
            return [d['participant_str'], 'videos', '{}.{}'.format(d['video_id'], file_ext)]

        self.download_items(video_dicts, epic_55_parts, epic_100_parts)

    def download_rgb_frames(self, video_dicts, file_ext='tar'):
        def epic_55_parts(d):
            return ['frames_rgb_flow', 'rgb', d['epic_55_split'], d['participant_str'],
                    '{}.{}'.format(d['video_id'], file_ext)]

        def epic_100_parts(d):
            return [d['participant_str'], 'rgb_frames', '{}.{}'.format(d['video_id'], file_ext)]

        self.download_items(video_dicts, epic_55_parts, epic_100_parts)

    def download_flow_frames(self, video_dicts, file_ext='tar'):
        def epic_55_parts(d):
            return ['frames_rgb_flow', 'flow', d['epic_55_split'], d['participant_str'],
                    '{}.{}'.format(d['video_id'], file_ext)]

        def epic_100_parts(d):
            return [d['participant_str'], 'flow_frames', '{}.{}'.format(d['video_id'], file_ext)]

        self.download_items(video_dicts, epic_55_parts, epic_100_parts)

    def download_object_detection_images(self, video_dicts, file_ext='tar'):
        # these are available for epic 55 only, but we will use the epic_100_parts func to create a consistent output
        # path
        epic_55_dicts = {k: v for k, v in video_dicts.items() if not v['extension']}

        def epic_55_parts(d):
            return ['object_detection_images', d['epic_55_split'], d['participant_str'],
                    '{}.{}'.format(d['video_id'], file_ext)]

        def epic_100_parts(d):
            return [d['participant_str'], 'object_detection_images', '{}.{}'.format(d['video_id'], file_ext)]

        self.download_items(epic_55_dicts, epic_55_parts, epic_100_parts)

    def download_metadata(self, video_dicts, file_ext='csv'):
        epic_100_dicts = {k: v for k, v in video_dicts.items() if v['extension']}

        def epic_100_accl_parts(d):
            return [d['participant_str'], 'meta_data', '{}-accl.{}'.format(d['video_id'], file_ext)]

        def epic_100_gyro_parts(d):
            return [d['participant_str'], 'meta_data', '{}-gyro.{}'.format(d['video_id'], file_ext)]

        self.download_items(epic_100_dicts, None, epic_100_accl_parts)
        self.download_items(epic_100_dicts, None, epic_100_gyro_parts)

    def download_items(self, video_dicts, epic_55_parts_func, epic_100_parts_func):
        for video_id, d in video_dicts.items():
            extension = d['extension']
            remote_parts = epic_100_parts_func(d) if extension else epic_55_parts_func(d)
            url = '/'.join([self.base_url_100 if extension else self.base_url_55] + remote_parts)
            output_path = os.path.join(self.base_output, *epic_100_parts_func(d))
            self.download_file(url, output_path)

    def download(self, what=('videos', 'rgb_frames', 'flow_frames'), participants='all', splits='all',
                 challenges='all', extension_only=False, epic55_only=False):

        video_dicts = {}

        if splits == 'all' and challenges == 'all':
            download_splits = self.challenges_splits
        elif splits == 'all':
            download_splits = [cs for cs in self.challenges_splits for c in challenges if c == cs.split('_')[0]]
        elif challenges == 'all':
            download_splits = [cs for cs in self.challenges_splits for s in splits if s in cs.partition('_')[2]]
        else:
            download_splits = [cs for cs in self.challenges_splits for c in challenges for s in splits
                               if c == cs.split('_')[0] and s in cs.partition('_')[2]]

        for ds in download_splits:
            if not extension_only and not epic55_only:
                vl = self.videos_per_split[ds]
            else:
                # we know that only one between extension_only and epic_55_only will be True
                vl = [v for v in self.videos_per_split[ds] if (extension_only and v['extension']) or
                                                              (epic55_only and not v['extension'])]

            if participants != 'all':
                vl = [v for v in vl if v['participant'] in participants]

            video_dicts.update({v['video_id']: v for v in vl})  # we use a dict to avoid duplicates

        # sorting the dictionary
        video_dicts = {k: video_dicts[k] for k in sorted(video_dicts.keys())}

        if epic55_only:
            source = 'EPIC 55'
        elif extension_only:
            source = 'EPIC 100 (extension only)'
        else:
            source = 'EPIC 100'

        what_str = ', '.join(' '.join(w.split('_')) for w in what)
        participants_str = 'all' if participants == 'all' else ', '.join(['P{:02d}'.format(p) for p in participants])

        print('Going to download: {}\n'
              'for challenges: {}\n'
              'splits: {}\n'
              'participants: {}\n'
              'data source: {}'.format(what_str, challenges, splits, participants_str, source))

        for w in what:
            print_header('| Downloading {} now |'.format(' '.join(w.split('_'))), char='-')
            func = getattr(self, 'download_{}'.format(w))
            func(video_dicts)


def create_parser():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument('--output_path', nargs='?', type=str, default=Path.home(),
                        help='Path where to download files. Default is {}'.format(Path.home()))
    parser.add_argument('--videos', dest='what', action='append_const', const='videos', help='Download videos')
    parser.add_argument('--rgb_frames', dest='what', action='append_const', const='rgb_frames',
                        help='Download rgb frames')
    parser.add_argument('--flow_frames', dest='what', action='append_const', const='flow_frames',
                        help='Download optical flow frames')
    parser.add_argument('--object_detection_images', dest='what', action='append_const',
                        const='object_detection_images', help='Download object detection images (only for EPIC 55)')
    parser.add_argument('--metadata', dest='what', action='append_const',
                        const='metadata', help='Download GoPro''s metadata (only for EPIC 100)')
    parser.add_argument('--consent_forms', dest='what', action='append_const', const='consent_forms',
                        help='Download consent_forms')
    parser.add_argument('--participants', nargs='?', type=str, default='all',
                        help='Specify participants IDs. You can specif a single participant, e.g. `--participants 1` '
                             'or a comma-separated list of them, e.g. `--participants 1,2,3`')
    parser.add_argument('--extension_only', action='store_true', help='Download extension only')
    parser.add_argument('--epic55_only', action='store_true', help='Download only EPIC 55\'s data')
    parser.add_argument('--action_recognition', dest='challenges', action='append_const', const='ar',
                        help='Download data for the action recognition challenge')
    parser.add_argument('--domain_adaptation', dest='challenges', action='append_const', const='da',
                        help='Download data for the domain adaptation challenge')
    parser.add_argument('--cross_modal_retrieval', dest='challenges', action='append_const', const='cmr',
                        help='Download data for the cross modal retrieval challenge')
    parser.add_argument('--train', dest='splits', action='append_const', const='train',
                        help='Download data from the training split (for action recognition and cross modal retrieval)')
    parser.add_argument('--val', dest='splits', action='append_const', const='val',
                        help='Download data from the validation split (for action recognition only)')
    parser.add_argument('--test', dest='splits', action='append_const', const='test',
                        help='Download data from the testing split (for action recognition and cross modal retrieval)')
    parser.add_argument('--source_train', dest='splits', action='append_const', const='source_train',
                        help='Download data from the source training split for domain adaptation')
    parser.add_argument('--source_test', dest='splits', action='append_const', const='source_test',
                        help='Download data from the source testing split for domain adaptation')
    parser.add_argument('--target_train', dest='splits', action='append_const', const='target_train',
                        help='Download data from the target training split for domain adaptation')
    parser.add_argument('--target_test', dest='splits', action='append_const', const='target_test',
                        help='Download data from the target testing split for domain adaptation')
    parser.add_argument('--val_source_train', dest='splits', action='append_const', const='val_source_train',
                        help='Download the smaller source train set used to validate hyper-parameters for domain '
                             'adaptation')
    parser.add_argument('--val_source_test', dest='splits', action='append_const', const='val_source_test',
                        help='Download the smaller source test set used to validate hyper-parameters for domain '
                             'adaptation')
    parser.add_argument('--val_target_train', dest='splits', action='append_const', const='val_target_train',
                        help='Download the smaller target train set used to validate hyper-parameters for domain '
                             'adaptation')
    parser.add_argument('--val_target_test', dest='splits', action='append_const', const='val_target_test',
                        help='Download the smaller target test set used to validate hyper-parameters for domain '
                             'adaptation')

    return parser


def parse_args(parser):
    args = parser.parse_args()

    assert not (args.extension_only and args.epic55_only), \
        'You can specify either --extension_only or --epic55_only, but not both'

    assert not (args.extension_only and ['object_detection_images'] == args.what), \
        'Object detection images are available only for EPIC 55'

    assert not (args.epic55_only and ['metadata'] == args.what), \
        'GoPro''s metadata is available only for EPIC 100'

    if args.what is None:
        args.what = ('videos', 'rgb_frames', 'flow_frames', 'object_detection_images', 'metadata', 'consent_forms')

    if args.challenges is None:
        args.challenges = 'all'

    if args.splits is None:
        args.splits = 'all'

    if args.participants != 'all':
        try:
            args.participants = [int(p.strip()) for p in args.participants.split(',')]
        except ValueError:
            print('Invalid participants arguments: {}.'
                  '\nYou can specif a single participant, e.g. `--participants 1` or\n'
                  'a comma-separated list of them, e.g. `--participants 1,2,3`.'.format(args.participants))
            exit(-1)

    return args


if __name__ == '__main__':
    assert sys.version_info.major == 3 and sys.version_info.minor >= 5, 'This script works with Python 3.5+. ' \
                                                                        'Please use a more recent Python version'

    parser = create_parser()
    args = parse_args(parser)

    print_header('*** Welcome to the EPIC Kitchens Downloader! ***')

    downloader = EpicDownloader(base_output=args.output_path)
    downloader.download(what=args.what, participants=args.participants, splits=args.splits, challenges=args.challenges,
                        extension_only=args.extension_only, epic55_only=args.epic55_only)

    print_header('*** All done, bye! ***')