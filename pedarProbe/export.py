"""Analysis result export functionalities. Short-cut functions are realised in :class:`pedarProbe.node.PedarNode` to facilitate the usability.
"""
from __future__ import annotations
from typing import Type, Union

import copy
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image, ImageOps

import node

def attribute_batch_export(node, attr_name: str, export_layer: str, export_folder='output', save_suffix: str = ''):
    """Batch export the analysis result of a specific layer in the node tree as a :code:`.xlsx` file.
    
    Parameters
    ---
    attr_name
        attribute name, which is a keyword in :class:`~pedarProbe.node.PedarNode`'s :attr:`attributes` dictionary.
    export_layer
            if export as local file, the name of the layer to export.
    export_folder
        the folder of the exported file.
    save_suffix
        the suffix added to the default export file name :code:`sensor_pti`.

        .. tip::
            A specific suffix can avoid exported file be override by future export.
    """
    export_level = node.loc_map[export_layer]
    row_name_list = []
    attribute_list = []

    export_nodes = node.collect_layer(export_layer, nodes=[])

    for node in export_nodes:
        row_name = ' '.join(node.loc[1 : export_level + 1])
        row_name_list.append(row_name)
        attribute_list.append(node.attribute[attr_name])
    
    # rearrange as a data frame and export
    df_condition = pd.DataFrame({"condition": row_name_list})
    df_data = pd.concat(attribute_list, axis=1).transpose()
    df_export = pd.concat([df_condition, df_data], axis=1)

    df_export.to_excel("{}/{}{}.xlsx".format(export_folder, attr_name, save_suffix))


class FootHeatmap(object):
    """Foot heatmap class.

    Parameters
    ---
    node
        the node that stores the data for generate foot heatmap.
    attr_name
        attribute name, which is a keyword in :class:`~pedarProbe.node.PedarNode`'s :attr:`attributes` dictionary.
    mask_dir
        directory of the mask file.
        
        .. tip::
            If Python interpretor is run at the same directory as :code:`node.py`, :attr:`mask_dir` should be :code:`data/left_foot_mask.png`, i.e. the default value.

        .. attention::
            During python runtime, the foot sensor mask is loaded in the first instantiating of :class:`FootHeatmap` and then other :class:`FootHeatmap` all shares the same loaded mask. Therefore, :attr:`mask_dir` is only needed to be passed in for the first instantiating of :class:`FootHeatmap`.

    Note
    ---
    `Class Attributes`
    
    self.l_pedar :class:`numpy.ndarray`
        left foot attribute distribution.
    self.r_pedar
        left foot attribute distribution.
    """
    l_index = None
    """
    :class:`dict` that stores the pixel coordinates of different left foot sensor areas, which sensor ID 0~98 as the keywords. Initialised as :code:`None`.
    """
    r_index = None
    """
    :class:`dict` that stores the pixel coordinates of different right foot sensor areas, which sensor ID 99~197 as the keywords. Initialised as :code:`None`.
    """

    def __init__(self, node: Type[node.Node], attr_name: str = 'sensor_peak', mask_dir: str = 'data/left_foot_mask.png'):
        # if foot mask has never been loaded, call load_foot_mask() method
        if self.l_index is None:
            self.load_foot_mask(mask_dir)

        self.fill_foot_heat_map(node, attr_name)

    @classmethod
    def load_foot_mask(cls, mask_dir: str = 'data/left_foot_mask.png'):
        """Load foot mask, detect the pixel coordinates belonging to 0~198 sensor areas, and store them in :attr:`cls.l_index` and :attr:`cla.r_index`.
        
        Parameters
        ---
        mask_dir
            directory of the mask file.

        Attention
        ---
        Being called in the first instantiating of :class:`FootHeatmap` by :meth:`__init__`.
        """
        # load the left foot mask image
        # flip it as the right foot mask image
        l_img = Image.open(mask_dir)
        r_img = ImageOps.mirror(l_img)

        l_mask = np.array(l_img).astype(np.float64)
        r_mask = np.array(r_img).astype(np.float64)

        cls.l_shape = l_mask.shape
        cls.r_shape = r_mask.shape

        # detect pixels of area no.1~197 and store the corresponding indexes
        cls.l_index = {}
        cls.r_index = {}

        for n in range(0, 198):
            cls.l_index[n] = np.where(l_mask == n + 1)
            cls.r_index[n + 99] = np.where(r_mask == n + 1)

    def fill_foot_heat_map(self, node: Type[node.Node], attr_name: str = 'sensor_peak'):
        """Fill attribute value to distribution according to :attr:`cls.l_index` and :attr:`cla.r_index`.
        
        Parameters
        ---
        node
            the node that stores the data for generate foot heatmap.
        attr_name
            attribute name, which is a keyword in :class:`~pedarProbe.node.PedarNode`'s :attr:`attributes` dictionary.

        Attention
        ---
        called by :meth:`__init__`.
        """
        # create empty left and right distribution
        self.l_pedar = np.zeros(self.l_shape)
        self.r_pedar = np.zeros(self.r_shape)

        # fill the attribute distribution
        for n in node.attribute[attr_name].index:
            if n <= 99:
                # filling left foot area
                self.l_pedar[self.l_index[n]] = node.attribute[attr_name][n]
            else:
                # filling right foot area
                self.r_pedar[self.r_index[n]] = node.attribute[attr_name][n]

    def export_foot_heatmap(self, range: Union[str, tuple] = 'static', is_export: bool = True, export_folder: str = 'output', save_suffix: str = ''):
        """Plot and export the foot heatmap.
        
        Parameters
        ---
        range
            The color mapping range.

            - :code:`'static'`: map value :math:`\in [0, 300]` to color, suitable for pressure distribution heatmap.
            - :code:`'auto'`: automatically detect the value range, suitable for other attribute distribution heatmap.
            - manually setting the color mapping range with a :class:`tuple` in the format of :code:`(<min, max>)`, suitable for generating various heatmap with a unified color mapping range.

            .. attention::
                Value lower (higher) than the lower (higher) range will be mapped as the lowest (highest) color in the color bar.

        is_export
            export the analysed result as a local file or not.
        export_folder
            the folder of the exported file.
        save_suffix
            the suffix added to the default export file name :code:`foot_heatmap`.

            .. tip::
                A specific suffix can avoid exported file be override by future export.
        """
        # value range
        if range == 'static':
            range_min = 0
            range_max = 300
        elif range == 'auto':
            range_min = np.min([np.min(self.l_pedar), np.min(self.r_pedar)])
            range_max = np.max([np.max(self.l_pedar), np.max(self.r_pedar)])
        else:
            # manually control with a tuple of (min, max)
            range_min, range_max = range

        # show and export as heatmap
        fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(7, 8))
        l_img = axes[0].imshow(self.l_pedar, cmap='cool', vmin=range_min, vmax=range_max)
        r_img = axes[1].imshow(self.r_pedar, cmap='cool', vmin=range_min, vmax=range_max)

        fig.subplots_adjust(right=0.85)
        cbar_ax = fig.add_axes([0.88, 0.15, 0.04, 0.7])
        fig.colorbar(r_img, cbar_ax)
        plt.show()

        if is_export:
            fig.savefig('{}/foot_heatmap{}'.format(export_folder, save_suffix))

    def __add__(self, other: Type[FootHeatmap]) -> Type[FootHeatmap]:
        """Magic method of adding."""
        new_hm = copy.deepcopy(self)
        new_hm.l_pedar += other.l_pedar
        new_hm.r_pedar += other.r_pedar
        return new_hm

    def __sub__(self, other: Type[FootHeatmap]) -> Type[FootHeatmap]:
        """Magic method of subtraction."""
        new_hm = copy.deepcopy(self)
        new_hm.l_pedar -= other.l_pedar
        new_hm.r_pedar -= other.r_pedar
        return new_hm

    def __mul__(self, val: Union[float, int]) -> Type[FootHeatmap]:
        """Magic method of multiplication."""
        new_hm = copy.deepcopy(self)
        new_hm.l_pedar *= val
        new_hm.r_pedar *= val
        return new_hm

    def __truediv__(self, val: Union[float, int]) -> Type[FootHeatmap]:
        """Magic method of true division."""
        new_hm = copy.deepcopy(self)
        new_hm.l_pedar /= val
        new_hm.r_pedar /= val
        return new_hm

    @staticmethod
    def average(*hms):
        """Return an averaged heatmap object of the inputted heatmap objects.
        
        Parameters
        ---
        *hms
            inputted heatmap objects for average.
        """
        # start parameter of sum() is an int, which cause issue
        # therefore set the start of sum as hms[0] and the others as hms[1:]
        return sum(hms[1:], start=hms[0]) / len(hms)