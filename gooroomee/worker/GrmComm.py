import time
import hp2papi as api

from GUI.MainWindow import MainWindowClass
from gooroomee.bin_comm import BINComm
from gooroomee.grm_defs import GrmParentThread, MediaQueueData
from gooroomee.grm_packet import BINWrapper, TYPE_INDEX
from gooroomee.grm_queue import GRMQueue


class GrmCommWorker(GrmParentThread):
    def __init__(self,
                 main_window,
                 p_send_audio_queue,
                 p_send_video_queue,
                 p_send_chat_queue,
                 p_recv_audio_queue,
                 p_recv_video_queue,
                 p_is_server,
                 p_ip_address,
                 p_port_number,
                 p_device_type,
                 p_set_connect,
                 p_get_global_comm_grm_type):
        super().__init__()
        # self.main_windows: MainWindowClass = p_main_windows
        self.main_window: MainWindowClass = main_window
        self.comm_bin = None
        self.client_connected: bool = False
        # self.lock = None
        self.sent_key_frame = False
        self.send_audio_queue: GRMQueue = p_send_audio_queue
        self.send_video_queue: GRMQueue = p_send_video_queue
        self.send_chat_queue: GRMQueue = p_send_chat_queue
        self.recv_audio_queue: GRMQueue = p_recv_audio_queue
        self.recv_video_queue: GRMQueue = p_recv_video_queue
        self.avatar = None
        self.kp_source = None
        self.avatar_kp = None
        self.bin_wrapper = BINWrapper()
        self.is_server = p_is_server
        self.ip_address = p_ip_address
        self.port_number = p_port_number
        self.device_type = p_device_type
        self.set_connect = p_set_connect
        self.get_global_comm_grm_type = p_get_global_comm_grm_type

    def on_client_connected(self):
        print('grm_worker:on_client_connected')
        # self.lock.acquire()
        self.client_connected = True
        self.sent_key_frame = False
        self.set_connect(True)
        # self.lock.release()

    def on_client_closed(self):
        print('grm_worker:on_client_closed')
        # self.lock.acquire()
        self.client_connected = False
        self.sent_key_frame = False
        # self.set_join(False)
        # self.main_windows.set_connect(False)
        # self.lock.release()

    def on_client_data(self, bin_data):
        if self.client_connected is False:
            self.client_connected = True
            self.set_connect(True)
        if self.join_flag is False:
            return

        _version, _timestamp, _seqnum, _ssrc, _mediatype, _bindata_len, _bindata = self.bin_wrapper.parse_wrap_common_header(
            bin_data)
        if _mediatype == TYPE_INDEX.TYPE_VIDEO:
            media_queue_data = MediaQueueData("", _bindata)
            self.recv_video_queue.put(media_queue_data)
        elif _mediatype == TYPE_INDEX.TYPE_AUDIO:
            media_queue_data = MediaQueueData("", _bindata)
            self.recv_audio_queue.put(media_queue_data)
        elif _mediatype == TYPE_INDEX.TYPE_DATA:
            _type, _value, _ = self.bin_wrapper.parse_bin(_bindata)
            if _type == TYPE_INDEX.TYPE_DATA_CHAT:
                chat_message = self.bin_wrapper.parse_chat(_value)
                print(f"chat_message : {chat_message}")
                self.main_window.output_chat(chat_message)

    def run(self):
        if self.get_global_comm_grm_type() is True:
            if self.comm_bin is None:
                self.comm_bin = BINComm()
            print(
                f"is_server:{self.is_server}, comm_bin:{self.comm_bin}, "
                f"client_connected:{self.client_connected}")
            if self.is_server is True:
                if self.client_connected is False:
                    self.comm_bin.start_server(self.port_number, self.on_client_connected,
                                               self.on_client_closed, self.on_client_data)
                    print(f'######## run server [{self.port_number}]. device:{self.device_type}')
            else:
                if self.client_connected is False:
                    print(
                        f'######## run client (connect ip:{self.ip_address}, '
                        f'connect port:{self.port_number}). device:{self.device_type}')
                    self.comm_bin.start_client(self.ip_address, self.port_number,
                                               self.on_client_connected, self.on_client_closed, self.on_client_data)

        while self.alive:
            print(f'GrmCommWorker running:{self.running}')
            while self.running:
                # print(f'GrmCommWorker queue size:{self.send_audio_queue.length()}')
                if self.send_audio_queue.length() > 0:
                    # print(f'GrmCommWorker pop queue size:{self.send_audio_queue.length()}')
                    audio_bin_data = self.send_audio_queue.pop()
                    if audio_bin_data is not None:
                        if self.get_global_comm_grm_type() is True:
                            if self.join_flag is True:
                                if self.client_connected is True:
                                    self.comm_bin.send_bin(audio_bin_data)
                        else:
                            audio_channel_id = self.main_window.join_session.audio_channel_id()
                            if audio_channel_id is not None:
                                send_request = api.SendDataRequest(api.DataType.Data,
                                                                   self.main_window.join_session.overlayId,
                                                                   self.main_window.join_session.audio_channel_id(),
                                                                   audio_bin_data)
                                # print("\nSendData Request:", send_request)

                                res = api.SendData(send_request)
                                # print("\nSendData Response:", res)

                                if res.code is api.ResponseCode.Success:
                                    # print("Video SendData success")
                                    pass
                                else:
                                    print("Audio SendData fail.", res.code)

                # print(f'GrmCommWorker queue size:{self.video_packet_queue.length()}')
                if self.send_video_queue.length() > 0:
                    # print(f'GrmCommWorker pop queue size:{self.send_video_queue.length()}')
                    video_bin_data = self.send_video_queue.pop()
                    if video_bin_data is not None:
                        if self.get_global_comm_grm_type() is True:
                            if self.join_flag is True:
                                if self.client_connected is True:
                                    self.comm_bin.send_bin(video_bin_data)
                        else:
                            video_channel_id = self.main_window.join_session.video_channel_id()
                            if video_channel_id is not None:
                                send_request = api.SendDataRequest(api.DataType.Data,
                                                                   self.main_window.join_session.overlayId,
                                                                   self.main_window.join_session.video_channel_id(),
                                                                   video_bin_data)
                                # print("\nSendData Request:", send_request)

                                res = api.SendData(send_request)
                                # print("\nSendData Response:", res)

                                if res.code is api.ResponseCode.Success:
                                    # print("Video SendData success")
                                    pass
                                else:
                                    print("Video SendData fail.", res.code)

                if self.send_chat_queue.length() > 0:
                    # print(f'GrmCommWorker pop queue size:{self.send_chat_queue.length()}')
                    chat_bin_data = self.send_chat_queue.pop()
                    if chat_bin_data is not None:
                        text_channel_id = self.main_window.join_session.text_channel_id()
                        if text_channel_id is not None:
                            send_request = api.SendDataRequest(api.DataType.Data,
                                                               self.main_window.join_session.overlayId,
                                                               self.main_window.join_session.text_channel_id(),
                                                               chat_bin_data)
                            # print("\nSendData Request:", send_request)

                            res = api.SendData(send_request)
                            # print("\nSendData Response:", res)

                            if res.code is api.ResponseCode.Success:
                                # print("Video SendData success")
                                pass
                            else:
                                print("Chat SendData fail.", res.code)

                time.sleep(0.1)
            time.sleep(0.1)

        print("Stop GrmCommWorker")
        self.terminated = True
        # self.terminate()

