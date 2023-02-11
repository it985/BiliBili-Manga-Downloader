from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QWidget

from src.Episode import Episode
from src.utils import DownloadInfo, openFolderAndSelectItems

if TYPE_CHECKING:
    from src.ui.MainGUI import MainGUI


class DownloadUI(QObject):
    """下载UI类，用于管理下载任务以及相关进度条等信息的显示更新
    """

    #?###########################################################
    #? 信号槽，用于更新下载进度条
    rate_progress = Signal(dict)

    def __init__(self, mainGUI: MainGUI):
        super().__init__()
        self.id_count = 0
        self.all_tasks = {}
        self.download_info = DownloadInfo()
        self.executor = ThreadPoolExecutor(max_workers=mainGUI.getConfig("num_thread"))

        self.init_DownloadUI(mainGUI)

    ############################################################
    def init_DownloadUI(self, mainGUI: MainGUI) -> None:
        """初始化下载UI的相关事件绑定

        Args:
            mainGUI (MainGUI): 主窗口类实例
        """
        mainGUI.verticalLayout_processing.setAlignment(Qt.AlignTop)
        mainGUI.verticalLayout_finished.setAlignment(Qt.AlignTop)

        #?###########################################################
        #? 任务进度更新的信号槽绑定
        def _(result: dict):
            curr_task = self.all_tasks[result['taskID']]
            curr_task['rate'] = result['rate']
            curr_task['bar'].setValue(result['rate'])
            mainGUI.progressBar_total_progress.setValue(
                sum(self.all_tasks[i]['rate'] for i in self.all_tasks.keys())
                / len(self.all_tasks)
            )
            self.download_info.updateTask(result['taskID'], result['rate'])

            #? 更新总进度条的速度和剩余时间
            mainGUI.label_total_progress_speed.setText(f"{self.download_info.getTotalSmoothSpeedStr()}")
            mainGUI.label_total_progress_time.setText(f"{self.download_info.getTotalRemainingTimeStr()}")

            #? 在下载列表UI里删除下载完成的任务
            #? 如果result['rate'] 等于1 意味着下载出错跳过，删除任务相关信息
            if result['rate'] in (100, -1):
                for i in reversed(range(mainGUI.verticalLayout_processing.count())):
                    to_delete = mainGUI.verticalLayout_processing.itemAt(i).widget()
                    #? 如果widget的ObjectName和当前任务的id一致
                    if to_delete.objectName() == result['taskID']:
                        if result['rate'] == 100:
                            #? 取出标题组件用于添加到已完成列表
                            label_title = to_delete.layout().itemAt(0).widget()
                            self.addFinished(mainGUI, label_title, result['path'])
                        #? deleteLater 会有延迟，为了显示效果，先将父控件设为None
                        to_delete.setParent(None)
                        to_delete.deleteLater()

                #? 删除字典中的条目
                del curr_task
                self.download_info.removeTask(result['taskID'])
                self.all_tasks.pop(result['taskID'])

        self.rate_progress.connect(_)

        #?###########################################################
        #? 绑定清空已完成列表按钮
        def _():
            for i in reversed(range(mainGUI.verticalLayout_finished.count())):
                to_delete = mainGUI.verticalLayout_finished.itemAt(i).widget()
                to_delete.setParent(None)
                to_delete.deleteLater()

        mainGUI.pushButton_clear_tasks.clicked.connect(_)


    ############################################################
    def addFinished(self, mainGUI: MainGUI, label_title: QWidget, path: str) -> None:
        """添加已完成任务到已完成列表

        Args:
            mainGUI (MainGUI): 主窗口类实例
            label_title (QWidget): 标题组件
            path (str): 保存路径
        """
        #?###########################################################
        #? 添加到已完成列表
        h_layout_donwlowd_list = QHBoxLayout()
        h_layout_donwlowd_list.addWidget(label_title)
        h_layout_donwlowd_list.addStretch(1)

        #?###########################################################
        #? 超链接打开保存路径
        label_file_path = QLabel("<a href='file:///'>打开文件夹</a>")
        label_file_path.linkActivated.connect(lambda: openFolderAndSelectItems(path))
        h_layout_donwlowd_list.addWidget(label_file_path)

        widget = QWidget()
        widget.setLayout(h_layout_donwlowd_list)
        mainGUI.verticalLayout_finished.addWidget(widget)

    ############################################################
    def addTask(self, mainGUI: MainGUI, epi: Episode) -> None:
        """添加下载任务

        Args:
            epi (Episode): 漫画章节类实例
        """
        #?###########################################################
        #? 初始化储存文件夹
        if not os.path.exists(epi.save_path):
            os.makedirs(epi.save_path)

        #?###########################################################
        #? 创建任务
        task_id = str(self.id_count)
        self.download_info.createTask(task_id, epi.size)
        self.all_tasks[task_id] = {
            'rate': 0,
            'future': self.executor.submit(epi.download, mainGUI, self.rate_progress, task_id)
        }

        #?###########################################################
        #? 添加任务组件到正在下载列表
        h_layout_donwlowd_list = QHBoxLayout()
        h_layout_donwlowd_list.addWidget(QLabel(f"<span style='color:blue;font-weight:bold'>{epi.comic_name}</span>   >  {epi.title}"))
        bar = QProgressBar()
        bar.setTextVisible(True)

        self.all_tasks[task_id]['bar'] = bar
        h_layout_donwlowd_list.addWidget(bar)
        h_layout_donwlowd_list.setStretch(0, 1)
        h_layout_donwlowd_list.setStretch(1, 1)
        widget = QWidget()
        widget.setObjectName(task_id)
        widget.setLayout(h_layout_donwlowd_list)
        mainGUI.verticalLayout_processing.addWidget(widget)
        self.id_count += 1