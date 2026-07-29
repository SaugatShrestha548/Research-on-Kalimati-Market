"""Visualization helpers: create and export figures to figures/"""

import os

FIG_DIR = os.path.join(os.path.dirname(__file__), '..', 'figures')


def make_plots():
    os.makedirs(FIG_DIR, exist_ok=True)
    print('Visualization functions not yet implemented. Add plotting code in src/visualize.py')


if __name__ == '__main__':
    make_plots()
