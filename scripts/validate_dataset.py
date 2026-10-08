import argparse
from dataset_utils import validate
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',default='dataset/data.yaml');a=p.parse_args();print(validate(a.data)[1])
