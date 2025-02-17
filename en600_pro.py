import streamlit as st
import pandas as pd
import edge_tts
import asyncio
import os
import time
from pathlib import Path
import pygame
import wave
import soundfile as sf
from PIL import Image
import subprocess
import numpy as np
import traceback
import json
import base64
from gtts import gTTS
from pydub import AudioSegment
import io

## streamlit run en600st/en600_pro.py

# 기본 경로 설정
SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_PATH = SCRIPT_DIR / 'base/en600s-settings.json'
EXCEL_PATH = SCRIPT_DIR / 'base/en600new.xlsx'
TEMP_DIR = SCRIPT_DIR / 'temp'

# 필요한 디렉토리 생성
for dir_path in [SCRIPT_DIR / 'base', TEMP_DIR]:
    if not dir_path.exists():
        dir_path.mkdir(parents=True, exist_ok=True)

# 설정 파일이 없는 경우 기본 설정 생성
if not SETTINGS_PATH.exists():
    default_settings = {
        'first_lang': 'korean',
        'second_lang': 'english',
        'third_lang': 'none',
        'first_repeat': 0,
        'second_repeat': 1,
        'third_repeat': 0,
        'start_row': 1,
        'end_row': 50,
        'selected_sheet': 'en600 : 생활영어 600문장',
        'word_delay': 1,
        'spacing': 1.0,
        'subtitle_delay': 1.0,
        'next_sentence_time': 1.0,
        'english_speed': 1.2,
        'korean_speed': 1.2,
        'chinese_speed': 1.2,
        'japanese_speed': 1.2,
        'vietnamese_speed': 1.2,
        'keep_subtitles': True,
        'break_enabled': True,
        'break_interval': 10,
        'break_duration': 10,
        'auto_repeat': True,
        'repeat_count': 3,
        'english_font': 'Pretendard',
        'korean_font': 'Pretendard',
        'chinese_font': 'SimSun',
        'english_font_size': 32,
        'korean_font_size': 25,
        'chinese_font_size': 32,
        'japanese_font': 'PretendardJP-Light',
        'japanese_font_size': 28,
        'hide_subtitles': {
            'first_lang': False,
            'second_lang': False,
            'third_lang': False,
        },
        'english_color': '#FFFFFF',
        'korean_color': '#00FF00',
        'chinese_color': '#00FF00',
        'japanese_color': '#00FF00',
        'vietnamese_color': '#00FF00',
        'japanese_speed': 2.0,
        'vietnamese_font': 'Arial',
        'vietnamese_font_size': 30,
        'vietnamese_speed': 1.2,
        'healing_music': True,
        'healing_duration': 90,
        'voice_notification': True,
        'notification_voice': '선희',
    }
    with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
        json.dump(default_settings, f, ensure_ascii=False, indent=2)

# 엑셀 파일 존재 여부 확인
def create_default_excel():
    """기본 엑셀 파일 생성"""
    try:
        # 기본 데이터 생성 - 빈 데이터로 시작
        data = {
            'Sheet1': [
                ['English', 'Korean', 'Chinese', 'Vietnamese', 'Japanese']
            ]
        }
        
        # 엑셀 파일 생성
        with pd.ExcelWriter(EXCEL_PATH, engine='openpyxl') as writer:
            for sheet_name, sheet_data in data.items():
                df = pd.DataFrame(sheet_data[1:], columns=sheet_data[0])
                df.to_excel(writer, sheet_name=sheet_name, index=False, header=True)
        
        st.success("기본 엑셀 파일이 생성되었습니다.")
        return True
    except Exception as e:
        st.error(f"기본 엑셀 파일 생성 중 오류 발생: {e}")
        return False

# 엑셀 파일 존재 여부 확인 및 생성
if not EXCEL_PATH.exists():
    st.warning(f"엑셀 파일을 찾을 수 없습니다: {EXCEL_PATH}")
    st.info("기본 엑셀 파일을 생성합니다...")
    if create_default_excel():
        st.success("기본 엑셀 파일이 생성되었습니다. 이제 학습을 시작할 수 있습니다.")
    else:
        st.error("기본 엑셀 파일 생성에 실패했습니다. base 폴더에 en600new.xlsx 파일을 직접 넣어주세요.")

# 엑셀 파일에서 시트 목록 가져오기
def get_excel_sheets():
    """엑셀 파일에서 시트 목록 가져오기"""
    try:
        xl = pd.ExcelFile(EXCEL_PATH)
        sheet_names = xl.sheet_names
        
        # 시트 이름 매핑 수정
        sheet_display_names = {
            'Sheet1': 'en600 : 생활영어 600문장',
            'Sheet2': 'travel : 여행영어 800문장'
        }
        
        # 각 시트의 실제 데이터 행 수 확인
        sheet_info = {}
        for sheet in sheet_names:
            df = pd.read_excel(
                EXCEL_PATH,
                sheet_name=sheet,
                header=None,
                engine='openpyxl'
            )
            # 실제 데이터가 있는 마지막 행 찾기
            last_row = 0
            for i in range(len(df)):
                if df.iloc[i, 0].strip() == '' and df.iloc[i, 1].strip() == '' and df.iloc[i, 2].strip() == '':
                    break
                last_row = i + 1
            
            if last_row > 0:  # 데이터가 있는 시트만 포함
                # 매핑된 이름이 있으면 사용, 없으면 원래 이름 사용
                display_name = sheet_display_names.get(sheet, sheet)
                sheet_info[display_name] = last_row
        
        # 수정: 표시 이름으로 된 시트명 목록 반환
        return list(sheet_info.keys())
            
    except Exception as e:
        st.error(f"엑셀 시트 목록 가져오기 오류: {e}")
        return ['en600 : 생활영어 600문장']  # 기본값도 수정

def get_sheet_name_from_display(display_name):
    """표시용 시트명에서 실제 시트명 추출"""
    # 시트 이름 역매핑 수정
    sheet_name_mapping = {
        'en600 : 생활영어 600문장': 'Sheet1',
        'travel : 여행영어 800문장': 'Sheet2'
    }
    
    # 매핑된 실제 시트명이 있으면 반환, 없으면 원래 이름 사용
    return sheet_name_mapping.get(display_name, display_name)

# 엑셀 파일 읽기 함수
def read_excel_data(sheet_name='Sheet1'):
    """엑셀 파일 읽기 함수"""
    try:
        # 표시용 시트명에서 실제 시트명 추출
        actual_sheet_name = get_sheet_name_from_display(sheet_name)
        
        df = pd.read_excel(
            EXCEL_PATH,
            header=None,
            engine='openpyxl',
            sheet_name=actual_sheet_name
        )
        # 데이터 프레임이 비어있는지 확인
        if df.empty:
            st.error(f"선택한 시트 '{actual_sheet_name}'가 비어있습니다.")
            return None, 0
            
        # 최소 3개의 열(영어, 한국어, 중국어)이 있는지 확인
        if len(df.columns) < 3:
            st.error(f"선택한 시트 '{actual_sheet_name}'의 형식이 올바르지 않습니다. 최소 3개의 열(영어, 한국어, 중국어)이 필요합니다.")
            return None, 0
            
        # NaN 값을 빈 문자열로 대체
        df = df.fillna('')
        
        # 베트남어와 일본어 열이 없는 경우 빈 열 추가
        if len(df.columns) < 4:
            df[3] = ''  # 베트남어 열 추가
        if len(df.columns) < 5:
            df[4] = ''  # 일본어 열 추가
        
        # 실제 데이터가 있는 마지막 행 찾기
        last_row = 0
        for i in range(len(df)):
            if df.iloc[i, 0].strip() == '' and df.iloc[i, 1].strip() == '' and df.iloc[i, 2].strip() == '':
                break
            last_row = i + 1
        
        return df, last_row
    except Exception as e:
        st.error(f"엑셀 파일 읽기 오류: {e}")
        return None, 0

# base 폴더가 없으면 생성
if not (SCRIPT_DIR / 'base').exists():
    (SCRIPT_DIR / 'base').mkdir(parents=True)

# 언어 표시 매핑 수정
LANG_DISPLAY = {
    'korean': '한국어',
    'english': '영어',
    'chinese': '중국어',
    'japanese': '일본어',
    'vietnamese': '베트남어'  # 베트남어 추가
}

# 음성 매핑 정의 추가
VOICE_MAPPING = {
    'english': {
        "Jenny (US)": "en-US-JennyNeural",
        "Emma (US)": "en-US-EmmaNeural",
        "Aria (US)": "en-US-AriaNeural",
        "Sonia (UK)": "en-GB-SoniaNeural",
        "Guy (US)": "en-US-GuyNeural",
        "Roger (US)": "en-US-RogerNeural",
        "Brian (US)": "en-US-BrianNeural",
        "Steffan (US)": "en-US-SteffanNeural",
        "Ryan (UK)": "en-GB-RyanNeural",
        "Natasha (AU)": "en-AU-NatashaNeural",
        "William (AU)": "en-AU-WilliamNeural",
        "Molly (NZ)": "en-NZ-MollyNeural",
        "Mitchell (NZ)": "en-NZ-MitchellNeural",
        "Luna (SG)": "en-SG-LunaNeural",
        "Wayne (SG)": "en-SG-WayneNeural"
    },
    'korean': {
        "선희": "ko-KR-SunHiNeural",
        "인준": "ko-KR-InJoonNeural"
    },
    'chinese': {
        "샤오샤오 (여)": "zh-CN-XiaoXiaoNeural",
        "샤오이 (여)": "zh-CN-XiaoYiNeural",
        "샤오한 (여)": "zh-CN-XiaoHanNeural",
        "윈지엔 (남)": "zh-CN-YunjianNeural",
        "윈양 (남)": "zh-CN-YunyangNeural"
    },
    'japanese': {
        "Nanami": "ja-JP-NanamiNeural",
        "Keita": "ja-JP-KeitaNeural"
    },
    'vietnamese': {
        "HoaiMy": "vi-VN-HoaiMyNeural",
        "NamMinh": "vi-VN-NamMinhNeural"
    }
}

# 언어 설정
LANGUAGES = ['english', 'korean', 'chinese', 'japanese', 'vietnamese', 'none']

# 색상 매핑 추가
COLOR_MAPPING = {
    'white': '#FFFFFF',
    'black': '#000000',
    'green': '#00FF00',
    'blue': '#0000FF',
    'red': '#FF0000',
    'grey': '#808080',
    'ivory': '#FFFFF0',
    'pink': '#FFC0CB'
}

def initialize_session_state():
    """강제 초기화 추가"""
    if 'initialized' not in st.session_state:
        st.session_state.clear()
        st.session_state.initialized = True
        st.session_state.page = 'settings'
        
        # 설정 파일이 있으면 읽어오고, 없으면 기본값 사용
        if SETTINGS_PATH.exists():
            try:
                with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    # 재생 횟수를 정수로 변환하여 저장
                    settings['first_repeat'] = int(settings.get('first_repeat', 0))    # 기본값 0
                    settings['second_repeat'] = int(settings.get('second_repeat', 1))  # 기본값 1
                    settings['third_repeat'] = int(settings.get('third_repeat', 0))    # 기본값 0
                    st.session_state.settings = settings
            except Exception as e:
                st.error(f"설정 파일 로드 오류: {e}")
                st.session_state.settings = default_settings.copy()
        else:
            st.session_state.settings = default_settings.copy()
        
        st.session_state.settings_backup = None

    if 'user_language' not in st.session_state:
        st.session_state.user_language = 'korean'  # 기본값 설정

    # 학습 시간 관련 변수 초기화
    if 'start_time' not in st.session_state:
        st.session_state.start_time = time.time()
    
    # 오늘 날짜 확인
    current_date = time.strftime('%Y-%m-%d')
    
    # 학습 시간 파일 경로
    study_time_path = SCRIPT_DIR / 'study_time.json'
    
    # 파일에서 학습 시간 데이터 로드
    try:
        if study_time_path.exists():
            with open(study_time_path, 'r') as f:
                study_data = json.load(f)
                if study_data.get('date') == current_date:
                    st.session_state.today_total_study_time = study_data.get('time', 0)
                else:
                    st.session_state.today_total_study_time = 0
        else:
            st.session_state.today_total_study_time = 0
    except Exception:
        st.session_state.today_total_study_time = 0
    
    st.session_state.today_date = current_date
    st.session_state.last_update_time = time.time()

    # 다크 모드 감지
    is_dark_mode = st.get_option("theme.base") == "dark"
    
    # temp 폴더가 없으면 생성
    if not TEMP_DIR.exists():
        TEMP_DIR.mkdir(parents=True)
    
    if 'settings' not in st.session_state:
        # 설정 파일이 있으면서 필수 키가 모두 있는지 확인
        required_keys = {'jp_voice', 'vi_voice', 'japanese_speed', 'vietnamese_speed'}
        
        # 설정 마이그레이션 함수 수정
        def migrate_voice_settings(settings):
            # 중국어 음성 마이그레이션
            voice_migrations = {
                # 이전 버전 음성들을 새로운 형식으로 변환
                'XiaoXiao (CN)': '샤오샤오 (여)',
                'XiaoYi (CN)': '샤오이 (여)',
                'YunJian (CN)': '윈지엔 (남)',
                'YunYang (CN)': '윈양 (남)',
                'YunXi (CN)': '윈시 (남)',
                # 기존 한글 이름도 처리
                '샤오샤오': '샤오샤오 (여)',
                '윈시': '윈시 (남)',
                '윈지엔': '윈지엔 (남)',
                '윈양': '윈양 (남)'
            }
            
            if 'zh_voice' in settings:
                old_voice = settings['zh_voice']
                if old_voice in voice_migrations:
                    settings['zh_voice'] = voice_migrations[old_voice]
                elif old_voice not in VOICE_MAPPING['chinese']:
                    settings['zh_voice'] = '샤오샤오 (여)'  # 기본값을 샤오샤오로 설정
            
            return settings

        try:
            if SETTINGS_PATH.exists():
                with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
                    saved_settings = json.load(f)
                    # 설정 마이그레이션 수행
                    saved_settings = migrate_voice_settings(saved_settings)
                    
                    # 필수 키가 모두 있는지 확인
                    if all(key in saved_settings for key in required_keys):
                        # 테마에 따라 색상 업데이트
                        if is_dark_mode:
                            saved_settings.update({
                                'english_color': '#00FF00',
                                'korean_color': '#00FF00',
                                'chinese_color': '#00FF00',
                                'japanese_color': '#00FF00',
                                'vietnamese_color': '#00FF00',
                            })
                        else:
                            saved_settings.update({
                                'english_color': '#000000',
                                'korean_color': '#000000',
                                'chinese_color': '#000000',
                                'japanese_color': '#FFFFFF',
                                'vietnamese_color': '#FFFFFF',
                            })
                        st.session_state.settings = saved_settings
                        return
                    else:
                        # 필수 키가 없으면 설정 파일 삭제
                        os.remove(SETTINGS_PATH)
        except Exception as e:
            st.error(f"설정 파일 로드 중 오류: {e}")
            # 오류 발생 시 설정 파일 삭제
            if SETTINGS_PATH.exists():
                os.remove(SETTINGS_PATH)
        
        # 저장된 설정이 없거나 유효하지 않으면 기본값 사용
        st.session_state.settings = default_settings.copy()

    # break.wav 파일 존재 여부 확인
    break_sound_path = SCRIPT_DIR / './base/break.wav'
    if not break_sound_path.exists():
        st.warning("브레이크 알림음 파일이 없습니다. 기본 알림음을 생성합니다.")
        try:
            # 기본 알림음 생성 (북소리)
            communicate = edge_tts.Communicate("딩동", "ko-KR-SunHiNeural")
            asyncio.run(communicate.save(str(break_sound_path)))
        except Exception as e:
            st.error(f"알림음 생성 오류: {e}")

    # 설정 로드 시 백업 생성
    if 'settings' in st.session_state:
        st.session_state.settings_backup = st.session_state.settings.copy()

def create_settings_ui(return_to_learning=False):
    # 함수 시작 부분에 settings 초기화 추가
    if 'settings' not in st.session_state:
        st.session_state.settings = default_settings.copy()

    settings = st.session_state.settings

    # 설정 백업 복원 (취소 시 사용)
    if return_to_learning and 'settings_backup' in st.session_state:
        settings = st.session_state.settings_backup.copy()

    if return_to_learning:
        # 학습 중 설정 모드일 때
        if st.button("💾 저장 후 학습 재개", type="primary", key="save_and_resume_learning_1"):
            try:
                if save_settings(settings):
                    st.session_state.settings = settings.copy()
                    st.session_state.settings_backup = settings.copy()
                    st.session_state.page = 'learning'
                    st.rerun()
            except Exception as e:
                st.error(f"설정 저장 중 오류 발생: {str(e)}")
    else:
        # 기본 설정 모드일 때
        if st.button("💾 저장 후 학습 재개", type="primary", key="save_and_resume_learning_2"):
            try:
                if save_settings(settings):
                    st.session_state.settings = settings.copy()
                    st.session_state.settings_backup = settings.copy()
                    st.session_state.page = 'learning'
                    st.rerun()
            except Exception as e:
                st.error(f"설정 저장 중 오류 발생: {str(e)}")

    # 저장 버튼 스타일
    st.markdown("""
        <style>
            /* 저장 버튼 스타일 */
            div[data-testid="stButton"] > button:first-child {
                background-color: #00FF00 !important;
                color: black !important;
                width: 100% !important;
                margin-top: 1rem !important;
            }
            
            /* 빠른 선택 버튼 스타일 */
            div[data-testid="stButton"] > button {
                width: 100% !important;
                margin: 0.2rem 0 !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # 빠른 선택 버튼 스타일 추가
    st.markdown("""
        <style>
            /* 빠른 선택 버튼 스타일 */
            div[data-testid="stButton"] > button {
                width: 100% !important;
                margin: 0.2rem 0 !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # 시트 선택 옵션 추가
    sheet_names = get_excel_sheets()
    current_sheet_display = settings.get('selected_sheet', sheet_names[0])
    if current_sheet_display not in sheet_names:
        current_sheet_display = sheet_names[0]

    col1, col2 = st.columns([0.7, 0.3])
    with col1:
        selected_sheet_display = st.selectbox(
            "엑셀 시트 선택",
            options=sheet_names,
            index=sheet_names.index(current_sheet_display),
            key="sheet_select_main"
        )

    # 실제 시트명 추출
    selected_sheet = get_sheet_name_from_display(selected_sheet_display)

    # 시트가 변경되었을 때
    if selected_sheet != get_sheet_name_from_display(settings.get('selected_sheet', 'Sheet1')):
        df, last_row = read_excel_data(selected_sheet)
        if df is not None and last_row > 0:
            settings['selected_sheet'] = selected_sheet
            settings['start_row'] = 1
            settings['end_row'] = min(50, last_row)  # 기본값 50으로 제한
            st.info(f"시트 변경: 행 범위가 자동으로 조정. (1-{settings['end_row']})")

    # 선택된 시트의 행 수 표시
    try:
        df, last_row = read_excel_data(selected_sheet)
        if df is not None and last_row > 0:
            st.info(f"선택된 시트의 총 행 수: {last_row}")
            
            # 빠른 선택 버튼들
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("처음 50개", key="first_50_main"):
                    settings['start_row'] = 1
                    settings['end_row'] = min(50, last_row)
            
            with col2:
                if st.button("다음 50개", key="next_50_main"):
                    current_end = settings.get('end_row', 50)
                    settings['start_row'] = current_end + 1
                    settings['end_row'] = min(current_end + 50, last_row)
            
            with col3:
                if st.button("처음 100개", key="first_100_main"):
                    settings['start_row'] = 1
                    settings['end_row'] = min(100, last_row)
            
            with col4:
                if st.button("다음 100개", key="next_100_main"):
                    current_end = settings.get('end_row', 100)
                    settings['start_row'] = current_end + 1
                    settings['end_row'] = min(current_end + 100, last_row)
            
            # 수동 입력 필드
            col1, col2 = st.columns(2)
            with col1:
                settings['start_row'] = st.number_input(
                    "시작 행",
                    min_value=1,
                    max_value=last_row,
                    value=settings.get('start_row', 1)
                )
            
            with col2:
                settings['end_row'] = st.number_input(
                    "종료 행",
                    min_value=settings['start_row'],
                    max_value=last_row,
                    value=min(settings.get('end_row', last_row), last_row)
                )
            
            # 선택된 범위 표시
            st.info(f"선택된 범위: {settings['start_row']} - {settings['end_row']} (총 {settings['end_row'] - settings['start_row'] + 1}개)")
            
    except Exception as e:
        st.error(f"시트 정보 읽기 오류: {e}")

    # 언어 순서 설정 섹션의 제목 수정
    custom_subheader("자막 · 음성 · 속도")
    col1, col2, col3 = st.columns(3)
    
    # 1순위 언어 설정
    with col1:
        settings['first_lang'] = st.selectbox("1순위 언어",
            options=['korean', 'english', 'chinese', 'japanese', 'vietnamese'],
            index=['korean', 'english', 'chinese', 'japanese', 'vietnamese'].index(settings['first_lang']),
            format_func=lambda x: LANG_DISPLAY[x],
            key="settings_first_lang")
        
        # 재생 횟수 설정
        first_repeat = st.selectbox("재생 횟수",
            options=list(range(0, 3)),
            index=int(settings.get('first_repeat', 0)),
            key="first_repeat_select")
        
        settings['first_repeat'] = int(first_repeat)
        
        # 1순위 언어의 음성 선택
        first_lang_voices = VOICE_MAPPING[settings['first_lang']]
        voice_key = f"{settings['first_lang'][:2]}_voice"
        current_voice = settings.get(voice_key)
        if not current_voice or current_voice not in first_lang_voices:
            current_voice = list(first_lang_voices.keys())[0]
            settings[voice_key] = current_voice
        
        settings[voice_key] = st.selectbox("음성 선택",
            options=list(first_lang_voices.keys()),
            index=list(first_lang_voices.keys()).index(current_voice),
            key=f"first_voice")
        
        # 배속 설정
        speed_options = [0.8, 1, 1.5, 2, 2.5, 3, 3.5, 4]
        current_speed = float(settings.get(f"{settings['first_lang']}_speed", 1.2))
        closest_speed = min(speed_options, key=lambda x: abs(x - current_speed))
        settings[f"{settings['first_lang']}_speed"] = st.selectbox(
            "배속",
            options=speed_options,
            index=speed_options.index(closest_speed),
            format_func=lambda x: f"{x}배속",
            key=f"first_speed"
        )
    
    # 2순위 언어 설정
    with col2:
        settings['second_lang'] = st.selectbox("2순위 언어",
            options=['korean', 'english', 'chinese', 'japanese', 'vietnamese'],
            index=['korean', 'english', 'chinese', 'japanese', 'vietnamese'].index(settings['second_lang']),
            format_func=lambda x: LANG_DISPLAY[x],
            key="settings_second_lang")
        
        # 재생 횟수 설정
        second_repeat = st.selectbox("재생 횟수",
            options=list(range(0, 3)),
            index=int(settings.get('second_repeat', 1)),
            key="second_repeat_select")
    
        
        settings['second_repeat'] = int(second_repeat)
        
        # 2순위 언어의 음성 선택
        second_lang_voices = VOICE_MAPPING[settings['second_lang']]
        voice_key = f"{settings['second_lang'][:2]}_voice"
        current_voice = settings.get(voice_key)
        if not current_voice or current_voice not in second_lang_voices:
            current_voice = list(second_lang_voices.keys())[0]
            settings[voice_key] = current_voice
        
        settings[voice_key] = st.selectbox("음성 선택",
            options=list(second_lang_voices.keys()),
            index=list(second_lang_voices.keys()).index(current_voice),
            key=f"second_voice")
        
        # 배속 설정
        speed_options = [0.8, 1, 1.5, 2, 2.5, 3, 3.5, 4]
        current_speed = float(settings.get(f"{settings['second_lang']}_speed", 1.2))
        closest_speed = min(speed_options, key=lambda x: abs(x - current_speed))
        settings[f"{settings['second_lang']}_speed"] = st.selectbox(
            "배속",
            options=speed_options,
            index=speed_options.index(closest_speed),
            format_func=lambda x: f"{x}배속",
            key=f"second_speed"
        )

    # 3순위 언어 설정
    with col3:
        settings['third_lang'] = st.selectbox("3순위 언어",
            options=['none', 'korean', 'english', 'chinese', 'japanese', 'vietnamese'],
            index=['none', 'korean', 'english', 'chinese', 'japanese', 'vietnamese'].index(settings.get('third_lang', 'none')),
            format_func=lambda x: '없음' if x == 'none' else LANG_DISPLAY[x],
            key="settings_third_lang")
        
        # 3순위 언어가 '없음'이 아닐 때만 나머지 설정 표시
        if settings['third_lang'] != 'none':
            # 재생 횟수 설정
            third_repeat = st.selectbox("재생 횟수",
                options=list(range(0, 3)),
                index=int(settings.get('third_repeat', 0)),
                key="third_repeat_select")
        
            
            settings['third_repeat'] = int(third_repeat)
            
            # 3순위 언어의 음성 선택
            third_lang_voices = VOICE_MAPPING[settings['third_lang']]
            voice_key = f"{settings['third_lang'][:2]}_voice"
            current_voice = settings.get(voice_key)
            if not current_voice or current_voice not in third_lang_voices:
                current_voice = list(third_lang_voices.keys())[0]
                settings[voice_key] = current_voice
            
            settings[voice_key] = st.selectbox("음성 선택",
                options=list(third_lang_voices.keys()),
                index=list(third_lang_voices.keys()).index(current_voice),
                key=f"third_voice")
            
            # 배속 설정
            speed_options = [0.8, 1, 1.5, 2, 2.5, 3, 3.5, 4]
            current_speed = float(settings.get(f"{settings['third_lang']}_speed", 1.2))
            closest_speed = min(speed_options, key=lambda x: abs(x - current_speed))
            settings[f"{settings['third_lang']}_speed"] = st.selectbox(
                "배속",
                options=speed_options,
                index=speed_options.index(closest_speed),
                format_func=lambda x: f"{x}배속",
                key=f"third_speed"
            )

    # 언어 순서 설정 섹션 다음에 추가
    
    # 문장 재생 설정
    custom_subheader("문장 재생 설정")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        settings['word_delay'] = st.slider(
            "단어 사이 간격",
            min_value=0.5,
            max_value=3.0,
            value=float(settings.get('word_delay', 1.0)),
            step=0.1,
            format="%.1f초"
        )
    
    with col2:
        settings['spacing'] = st.slider(
            "문장 사이 간격",
            min_value=0.5,
            max_value=5.0,  # 최대값 5초로 변경
            value=float(settings.get('spacing', 1.0)),
            step=0.1,
            format="%.1f초"
        )
    
    with col3:
        settings['next_sentence_time'] = st.slider(
            "다음 문장 대기 시간",
            min_value=0.5,
            max_value=5.0,  # 최대값 5초로 변경
            value=float(settings.get('next_sentence_time', 1.0)),
            step=0.1,
            format="%.1f초"
        )

    # 폰트 설정
    custom_subheader("폰트 설정")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    # 각 언어별 폰트 설정
    for idx, (lang, display_name) in enumerate([
        ('english', '영어'), 
        ('korean', '한국어'), 
        ('chinese', '중국어'),
        ('japanese', '일본어'),
        ('vietnamese', '베트남어')
    ]):
        with [col1, col2, col3, col4, col5][idx]:
            # 폰트 크기
            settings[f'{lang}_font_size'] = st.slider(
                f"{display_name} 폰트 크기",
                min_value=12,
                max_value=48,
                value=int(settings.get(f'{lang}_font_size', 28))
            )
            
            # 폰트 색상
            color_options = {
                '#00FF00': '초록색',
                '#FFFFFF': '흰색',
                '#FF0000': '빨간색',
                '#0000FF': '파란색',
                '#FFFF00': '노란색'
            }
            settings[f'{lang}_color'] = st.selectbox(
                f"{display_name} 폰트 색상",
                options=list(color_options.keys()),
                format_func=lambda x: color_options[x],
                index=list(color_options.keys()).index(settings.get(f'{lang}_color', '#00FF00'))
            )

    # 학습 설정
    custom_subheader("학습 설정")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        settings['auto_repeat'] = st.checkbox(
            "자동 반복 재생",
            value=settings.get('auto_repeat', True)
        )
        if settings['auto_repeat']:
            settings['repeat_count'] = st.number_input(
                "반복 횟수",
                min_value=1,
                max_value=10,
                value=int(settings.get('repeat_count', 3))
            )
    
    with col2:
        settings['break_enabled'] = st.checkbox(
            "쉬는 시간 설정",
            value=settings.get('break_enabled', True)
        )
        if settings['break_enabled']:
            settings['break_interval'] = st.number_input(
                "쉬는 시간 간격(문장)",
                min_value=5,
                max_value=50,
                value=int(settings.get('break_interval', 10))
            )
        
        settings['break_duration'] = st.number_input(
            "쉬는 시간(초)",
            min_value=5,
            max_value=60,
            value=int(settings.get('break_duration', 10))
        )
    
    
    with col3:
        settings['healing_music'] = st.checkbox(
            "힐링타임 설정",
            value=settings.get('healing_music', True)
        )
        if settings['healing_music']:
            # 힐링타임 종류 선택
            settings['healing_type'] = st.selectbox(
                "힐링타임 종류",
                options=['파이널', '기타'],
                index=['파이널', '기타'].index(settings.get('healing_type', '파이널'))
            )
            # 힐링타임 시간 선택
            settings['healing_duration'] = st.selectbox(
                "힐링타임 시간(초)",
                options=[30, 60, 90, 120],
                index=[30, 60, 90, 120].index(settings.get('healing_duration', 90))
            )

    # 저장 버튼
    if st.button("💾 저장 후 학습 재개", type="primary", key="save_and_resume_learning_1"):
        # 재생 횟수 설정 확인
        st.write("저장 전 설정 확인:")
        st.write(f"1순위: {settings['first_repeat']}")
        st.write(f"2순위: {settings['second_repeat']}")
        st.write(f"3순위: {settings['third_repeat']}")
        
        if save_settings(settings):
            st.session_state.settings = settings.copy()
            st.session_state.settings_backup = settings.copy()
            st.session_state.page = 'learning'
            st.rerun()

async def create_audio(text, voice, speed=1.0):
    """
    음성 파일 생성 - 베트남어도 edge-tts 사용
    """
    try:
        if not text or not voice:
            return None

        # 베트남어도 edge-tts 사용
        if voice == 'vi-VN':
            voice = 'vi-VN-HoaiMyNeural'  # edge-tts의 베트남어 음성

        output_file = TEMP_DIR / f"temp_{int(time.time()*1000)}.wav"
        try:
            if speed > 1:
                rate_str = f"+{int((speed - 1) * 100)}%"
            else:
                rate_str = f"-{int((1 - speed) * 100)}%"

            communicate = edge_tts.Communicate(text, voice, rate=rate_str)
            await communicate.save(str(output_file))
            return str(output_file)

        except Exception as e:
            st.error(f"음성 생성 오류: {str(e)}")
            traceback.print_exc()
            if output_file.exists():
                output_file.unlink()
            return None

    except Exception as e:
        st.error(f"음성 생성 오류: {str(e)}")
        traceback.print_exc()
        return None

def create_learning_ui():
    """학습 화면 UI 생성"""
    
    # 상단 컬럼 생성 - 진행 상태와 배속 정보를 위한 컬럼
    col1, col2 = st.columns([0.7, 0.3])
    
    with col1:
        progress = st.progress(0)
        status = st.empty()
    
        # 배속 정보 표시
        speed_info = []
        
        # 한글 배속 정보
        ko_speed = st.session_state.settings['korean_speed']
        ko_speed_text = str(int(ko_speed)) if ko_speed == int(ko_speed) else f"{ko_speed:.1f}"
        speed_info.append(f"한글 {ko_speed_text}배")
        
        # 영어 배속 정보
        eng_speed = st.session_state.settings['english_speed']
        eng_speed_text = str(int(eng_speed)) if eng_speed == int(eng_speed) else f"{eng_speed:.1f}"
        speed_info.append(f"영어 {eng_speed_text}배")
        
        # 중국어 배속 정보
        zh_speed = st.session_state.settings['chinese_speed']
        zh_speed_text = str(int(zh_speed)) if zh_speed == int(zh_speed) else f"{zh_speed:.1f}"
        speed_info.append(f"중국어 {zh_speed_text}배")
        
        # 베트남어 배속 정보
        vn_speed = st.session_state.settings['vietnamese_speed']
        vn_speed_text = str(int(vn_speed)) if vn_speed == int(vn_speed) else f"{vn_speed:.1f}"
        speed_info.append(f"베트남어 {vn_speed_text}배")
        
        # 배속 정보를 하나의 문자열로 결합
        speed_display = " · ".join(speed_info)
    
    # 자막을 위한 빈 컨테이너
    subtitles = [st.empty() for _ in range(3)]

    # 모든 텍스트를 초록색으로 설정하는 CSS 추가
    st.markdown("""
        <style>
            div[data-testid="stMarkdownContainer"] p {
                color: #00FF00 !important;
            }
            div.stMarkdown p {
                color: #00FF00 !important;
            }
            .element-container div {
                color: #00FF00 !important;
            }
        </style>
    """, unsafe_allow_html=True)

    return progress, status, subtitles

async def create_break_audio():
    """브레이크 음성 생성"""
    break_msg = "쉬는 시간입니다, 5초간의 여유를 느껴보세요"
    break_voice = VOICE_MAPPING['korean']['선희']
    audio_file = await create_audio(break_msg, break_voice, 1.0)
    return audio_file

async def play_voice_in_order(lang_mapping, settings):
    """순서대로 음성 재생을 처리하는 별도 함수"""
    voice_list = []
    
    voice_settings = [
        (settings['first_lang'], int(settings.get('first_repeat', 0))),
        (settings['second_lang'], int(settings.get('second_repeat', 1))),
        (settings['third_lang'], int(settings.get('third_repeat', 0)))
    ]
    
    for lang, repeat in voice_settings:
        if repeat > 0:
            voice_data = {
                'text': lang_mapping[lang]['text'],
                'voice': lang_mapping[lang]['voice'],
                'speed': lang_mapping[lang]['speed'],
                'repeat': repeat,
                'lang': lang
            }
            voice_list.append(voice_data)

    play_key = f"play_{int(time.time() * 1000)}"
    
    for voice_data in voice_list:
        for r in range(voice_data['repeat']):
            try:
                audio_file = await create_audio(
                    voice_data['text'],
                    voice_data['voice'],
                    voice_data['speed']
                )
                
                if audio_file:
                    duration = play_audio(audio_file, play_key=play_key)
                    
                    # 재생 완료 대기
                    start_time = time.time()
                    while time.time() - start_time < duration:
                        if st.session_state.get(f"{play_key}_ended", False):
                            break
                        await asyncio.sleep(0.1)
                    
                    # 상태 초기화
                    st.session_state[f"{play_key}_ended"] = False
                    
                    # 반복 재생 간격
                    if r < voice_data['repeat'] - 1:
                        await asyncio.sleep(settings['spacing'])
                
            except Exception as e:
                st.error(f"Error playing {voice_data['lang']}: {str(e)}")
                continue
        
        # 다음 언어로 넘어가기 전 간격
        if voice_data != voice_list[-1]:
            await asyncio.sleep(settings['spacing'])

def play_audio(file_path, play_key=None):
    """음성 파일 재생"""
    try:
        if not file_path or not os.path.exists(file_path):
            return 0

        # WAV 파일 검증 및 재생 시간 계산
        try:
            with wave.open(file_path, 'rb') as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()
                duration = frames / float(rate)
        except Exception as e:
            # WAV 파일이 아닌 경우 soundfile로 시도
            try:
                with sf.SoundFile(file_path) as sound_file:
                    duration = len(sound_file) / sound_file.samplerate
            except Exception:
                st.error(f"오디오 파일 형식 오류: {file_path}")
                return 0

        # 파일을 바이트로 읽기
        with open(file_path, 'rb') as f:
            audio_bytes = f.read()
        audio_base64 = base64.b64encode(audio_bytes).decode()

        # 고유한 ID 생성
        audio_id = f"audio_{int(time.time() * 1000)}"
        
        # 재생 완료 상태 초기화
        if play_key:
            st.session_state[f"{play_key}_ended"] = False
        
        # HTML 오디오 요소 생성
        st.markdown(f"""
            <audio id="{audio_id}" autoplay="true">
                <source src="data:audio/wav;base64,{audio_base64}" type="audio/wav">
            </audio>
            <script>
                const audio = document.getElementById('{audio_id}');
                audio.onended = function() {{
                    this.remove();
                    if (window.streamlit) {{
                        window.streamlit.setComponentValue('{play_key}_ended', true);
                    }}
                }};
            </script>
        """, unsafe_allow_html=True)

        return duration

    except Exception as e:
        st.error(f"음성 재생 오류: {str(e)}")
        return 0
    finally:
        try:
            if file_path and TEMP_DIR in Path(file_path).parents:
                os.remove(file_path)
        except Exception:
            pass

async def start_learning():
    """학습 시작"""
    settings = st.session_state.settings  # 세션에 저장된 설정 불러오기
    
    # 음성 설정 검증 및 초기화
    voice_defaults = {
        'eng_voice': 'Jenny (US)',
        'kor_voice': '선희',
        'zh_voice': '샤오샤오 (여)',
        'jp_voice': 'Nanami',
        'vi_voice': 'HoaiMy'
    }
    
    # 음성 설정 검증
    for key, default in voice_defaults.items():
        lang = key.split('_')[0]  # eng, kor, zh, jp, vi
        lang_full = {'eng': 'english', 'kor': 'korean', 'zh': 'chinese', 'jp': 'japanese', 'vi': 'vietnamese'}[lang]
        
        if key not in settings or settings[key] not in VOICE_MAPPING[lang_full]:
            st.warning(f"Invalid {lang_full} voice setting. Resetting to default.")
            settings[key] = default
    
    # 나머지 코드는 그대로 유지
    sentence_count = 0
    repeat_count = 0
    
    try:
        # 엑셀 파일 읽기
        df, last_row = read_excel_data(settings['selected_sheet'])
        if df is None:
            st.error("엑셀 파일을 읽을 수 없습니다.")
            return
            
        # 행 범위 검증
        if settings['start_row'] > last_row or settings['end_row'] > last_row:
            st.error(f"선택한 행 범위가 유효하지 않습니다. (시트의 총 행 수: {last_row})")
            return
            
        start_idx = settings['start_row'] - 1
        end_idx = settings['end_row'] - 1
        
        # 기본 3개 언어 데이터 가져오기
        selected_data = df.iloc[start_idx:end_idx+1, :3]
        english = selected_data.iloc[:, 0].tolist()
        korean = selected_data.iloc[:, 1].tolist()
        chinese = selected_data.iloc[:, 2].tolist()
        
        # 베트남어와 일본어는 열이 있는 경우에만 가져오기
        vietnamese = df.iloc[start_idx:end_idx+1, 3].tolist() if len(df.columns) > 3 else [''] * len(english)
        japanese = df.iloc[start_idx:end_idx+1, 4].tolist() if len(df.columns) > 4 else [''] * len(english)
        
        total_sentences = len(english)
        
        # 데이터 유효성 검사
        if not all(english) or not all(korean) or not all(chinese):
            st.error("필수 언어(영어, 한국어, 중국어) 데이터가 비어있는 행이 있습니다.")
            return
            
    except PermissionError:
        st.error("엑셀 파일이 다른 프로그램에서 열려있습니다. 파일을 닫고 다시 시도해주세요.")
        return
    except Exception as e:
        st.error(f"엑셀 파일 읽기 오류: {e}")
        return

    # 학습 UI 생성
    progress, status, subtitles = create_learning_ui()
    
    # 상단 컨트롤 패널 - 학습 종료 및 설정 버튼
    with st.container():
        col1, col2, col3 = st.columns([0.6, 0.2, 0.2])
        with col2:
            if st.button("⚙️ 설정", key="settings_btn"):
                st.session_state.page = 'settings_from_learning'
                st.rerun()
        with col3:
            if st.button("⏹️ 종료", key="stop_btn"):
                st.session_state.page = 'settings'
                st.rerun()

    # 자막 표시를 위한 빈 컨테이너
    subtitles = [st.empty() for _ in range(3)]
    
    # 이전 문장 자막 저장용 변수
    prev_subtitles = {'second': None, 'third': None}

    # 자막 스타일 정의 - 전역 스타일로 변경
    st.markdown("""
        <style>
        div[data-testid="stMarkdownContainer"] .english-text { color: #FFFFFF !important; }
        div[data-testid="stMarkdownContainer"] .korean-text { color: #00FF00 !important; }
        div[data-testid="stMarkdownContainer"] .chinese-text { color: #00FF00 !important; }
        div[data-testid="stMarkdownContainer"] .japanese-text { color: #00FF00 !important; }
        div[data-testid="stMarkdownContainer"] .vietnamese-text { color: #00FF00 !important; }
        </style>
    """, unsafe_allow_html=True)

    while True:
        for i, (eng, kor, chn, jpn, vn) in enumerate(zip(english, korean, chinese, japanese, vietnamese)):
            # 언어별 텍스트와 음성 매핑
            lang_mapping = {
                'korean': {'text': kor, 'voice': VOICE_MAPPING['korean'][settings['kor_voice']], 'speed': settings['korean_speed']},
                'english': {'text': eng, 'voice': VOICE_MAPPING['english'][settings['eng_voice']], 'speed': settings['english_speed']},
                'chinese': {'text': chn, 'voice': VOICE_MAPPING['chinese'][settings['zh_voice']], 'speed': settings['chinese_speed']},
                'japanese': {'text': jpn, 'voice': VOICE_MAPPING['japanese'][settings['jp_voice']], 'speed': settings['japanese_speed']},
                'vietnamese': {'text': vn, 'voice': VOICE_MAPPING['vietnamese'][settings['vi_voice']], 'speed': settings['vietnamese_speed']}
            }
            
            progress.progress((i + 1) / total_sentences)
            
            # 진행 상태와 배속 정보 표시
            speed_info = []
            
            # 순위에 따라 실제 재생되는 음성의 배속만 표시
            for lang in [settings['first_lang'], settings['second_lang'], settings['third_lang']]:
                if lang == 'korean' and settings['first_repeat'] > 0:
                    ko_speed = settings['korean_speed']
                    ko_speed_text = str(int(ko_speed)) if ko_speed == int(ko_speed) else f"{ko_speed:.1f}"
                    speed_info.append(f"한글 {ko_speed_text}배")
                elif lang == 'english' and settings['second_repeat'] > 0:
                    eng_speed = settings['english_speed']
                    eng_speed_text = str(int(eng_speed)) if eng_speed == int(eng_speed) else f"{eng_speed:.1f}"
                    speed_info.append(f"영어 {eng_speed_text}배")
                elif lang == 'chinese' and settings['third_repeat'] > 0:
                    zh_speed = settings['chinese_speed']
                    zh_speed_text = str(int(zh_speed)) if zh_speed == int(zh_speed) else f"{zh_speed:.1f}"
                    speed_info.append(f"중국어 {zh_speed_text}배")
                elif lang == 'vietnamese' and settings['third_repeat'] > 0:  # 베트남어 추가
                    vn_speed = settings['vietnamese_speed']
                    vn_speed_text = str(int(vn_speed)) if vn_speed == int(vn_speed) else f"{vn_speed:.1f}"
                    speed_info.append(f"베트남어 {vn_speed_text}배")
            
            # 배속 정보를 하나의 문자열로 결합
            speed_display = " · ".join(speed_info)
            
            # 문장 번호 계산 (엑셀 행 번호 사용)
            sentence_number = start_idx + i + 1
            sentence_number_display = f"No.{sentence_number:03d}"
            
            # 현재 시간과 마지막 업데이트 시간의 차이를 계산
            current_time = time.time()
            time_diff = current_time - st.session_state.last_update_time
            
            # 1분(60초)마다 누적 시간 업데이트
            if time_diff >= 60:
                minutes_to_add = int(time_diff / 60)
                st.session_state.today_total_study_time += minutes_to_add
                st.session_state.last_update_time = current_time
                # 학습 시간 저장
                save_study_time()
            
            # 상태 표시
            status.markdown(
                f'<span style="color: red">{sentence_number_display}</span> | '
                f'<span style="color: #00FF00">{i+1}/{total_sentences}</span> | '
                f'<span style="color: #00FF00">{speed_display}</span> | '
                f'<span style="color: red">학습: {int((current_time - st.session_state.start_time) / 60):02d}분</span> | '
                f'<span style="color: #00FF00">오늘: {st.session_state.today_total_study_time:02d}분</span>',
                unsafe_allow_html=True
            )

            # 자막 표시 부분
            for rank, (lang, repeat) in enumerate([
                (settings['first_lang'], settings['first_repeat']),
                (settings['second_lang'], settings['second_repeat']),
                (settings['third_lang'], settings['third_repeat'])
            ]):
                if lang == 'none':
                    continue
                    
                if not settings.get('hide_subtitles', {}).get(f'{["first", "second", "third"][rank]}_lang', False):
                    text = lang_mapping[lang]['text']
                    font = settings.get(f'{lang}_font', 'Arial')
                    size = settings.get(f'{lang}_font_size', 28)
                    
                    # 자막 표시
                    subtitles[rank].markdown(
                        f'<div class="{lang}-text" style="font-family: {font}; font-size: {size}px;">{text}</div>',
                        unsafe_allow_html=True
                    )

            # 음성 재생 - 새로운 함수 사용
            await play_voice_in_order(lang_mapping, settings)

            # 다음 문장으로 넘어가기 전 대기
            await asyncio.sleep(settings['next_sentence_time'])

            # 브레이크 체크
            sentence_count += 1
            if settings['break_enabled'] and sentence_count % settings['break_interval'] == 0:
                try:
                    status.warning(f"🔄 {settings['break_interval']}문장 완료! {settings['break_duration']}초간 휴식...")
                    
                    # 1. 먼저 break.wav 알림음 재생
                    break_sound_path = SCRIPT_DIR / 'base/break.wav'
                    if break_sound_path.exists():
                        play_audio(str(break_sound_path))
                        await asyncio.sleep(1)  # 알림음이 완전히 재생될 때까지 대기
                    
                    # 2. 브레이크 음성 메시지 생성 및 재생
                    break_msg = "쉬는 시간입니다, 5초간의 휴식을 느껴보세요"
                    break_audio = await create_audio(break_msg, VOICE_MAPPING['korean']['선희'], 1.0)
                    if break_audio:
                        play_audio(break_audio)
                        # 음성 메시지 재생 시간 계산 (대략적으로 메시지 길이에 따라)
                        await asyncio.sleep(3)  # 메시지가 재생될 때까지 대기
                    
                    # 3. 남은 휴식 시간 대기
                    remaining_time = max(0, settings['break_duration'] - 4)  # 알림음과 메시지 재생 시간을 고려
                    if remaining_time > 0:
                        await asyncio.sleep(remaining_time)
                    
                    status.empty()
                    
                except Exception as e:
                    st.error(f"브레이크 처리 중 오류: {e}")
                    traceback.print_exc()

        # 학습 완료 시
        try:
            # 마지막 시간 업데이트
            current_time = time.time()
            time_diff = current_time - st.session_state.last_update_time
            if time_diff >= 60:
                minutes_to_add = int(time_diff / 60)
                st.session_state.today_total_study_time += minutes_to_add
                st.session_state.last_update_time = current_time
                # 학습 시간 저장
                save_study_time()
            
            # final.wav 재생
            final_sound_path = SCRIPT_DIR / 'base/final.wav'
            if final_sound_path.exists():
                play_audio(str(final_sound_path))
                await asyncio.sleep(1)
            
            if settings['auto_repeat']:
                repeat_count += 1
                if repeat_count < settings['repeat_count']:
                    # 반복 횟수가 남았으면 처음부터 다시 시작
                    sentence_count = 0
                    status.info(f"반복 중... ({repeat_count}/{settings['repeat_count']})")
                    continue
                else:
                    # 반복 횟수를 모두 채우면 학습 종료
                    st.success(f"학습이 완료되었습니다! (총 {settings['repeat_count']}회 반복)")
                    st.session_state.page = 'settings'
                    st.rerun()
            
        except Exception as e:
            st.error(f"완료 알림음 재생 오류: {e}")
            traceback.print_exc()

def create_personalized_ui():
    """개인별 맞춤 UI 생성"""
    st.title("개인별 설정 기억하기")

    # 언어 선택
    selected_language = st.selectbox(
        "사용할 언어를 선택하세요",
        options=['korean', 'english', 'chinese', 'japanese', 'vietnamese'],
        index=['korean', 'english', 'chinese', 'japanese', 'vietnamese'].index(st.session_state.user_language)
    )
    # 선택한 언어를 세션 상태에 저장
    if selected_language != st.session_state.user_language:
        st.session_state.user_language = selected_language
        st.rerun()  # 변경된 언어를 반영하기 위해 페이지 새로고침

    # 선택한 언어에 따라 메시지 표시
    if st.session_state.user_language == 'korean':
        st.write("안녕하세요! 한국어로 표시됩니다.")
    elif st.session_state.user_language == 'english':
        st.write("Hello! This is displayed in English.")
    elif st.session_state.user_language == 'chinese':
        st.write("你好！这是用中文显示的。")
    elif st.session_state.user_language == 'japanese':
        st.write("こんにちは！これは日本語で表示されます。")
    else:  # vietnamese
        st.write("Xin chào! Đây là dòng chữ tiếng Việt.")

def main():
    initialize_session_state()
    
    # 페이지 라우팅
    if st.session_state.page == 'settings':
        create_settings_ui()
    elif st.session_state.page == 'settings_from_learning':
        create_settings_ui(return_to_learning=True)  # 학습 중 설정 모드
    elif st.session_state.page == 'learning':
        asyncio.run(start_learning())  # 학습 시작
    elif st.session_state.page == 'personalized':
        create_personalized_ui()

def save_settings(settings):
    """설정값을 파일에 저장"""
    try:
        # 재생 횟수를 정수로 변환
        settings['first_repeat'] = int(settings['first_repeat'])
        settings['second_repeat'] = int(settings['second_repeat'])
        settings['third_repeat'] = int(settings['third_repeat'])
        
        # 설정 파일 저장 전 백업 생성
        if SETTINGS_PATH.exists():
            backup_path = SETTINGS_PATH.with_suffix('.json.bak')
            import shutil
            shutil.copy2(SETTINGS_PATH, backup_path)
        
        # 새로운 설정 저장
        with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        
        # 저장된 설정 확인
        with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
            saved_settings = json.load(f)
            if (saved_settings['first_repeat'] != settings['first_repeat'] or
                saved_settings['second_repeat'] != settings['second_repeat'] or
                saved_settings['third_repeat'] != settings['third_repeat']):
                st.error("설정이 제대로 저장되지 않았습니다.")
                return False
        
        return True
        
    except Exception as e:
        st.error(f"설정 저장 중 오류: {e}")
        return False

def save_study_time():
    """학습 시간을 파일에 저장"""
    study_time_path = SCRIPT_DIR / 'study_time.json'
    try:
        with open(study_time_path, 'w') as f:
            json.dump({
                'date': st.session_state.today_date,
                'time': st.session_state.today_total_study_time
            }, f)
    except Exception as e:
        st.error(f"학습 시간 저장 중 오류: {e}")

def get_setting(key, default_value):
    """안전하게 설정값을 가져오는 유틸리티 함수"""
    return st.session_state.settings.get(key, default_value)

def save_learning_state(df, current_index, session_state):
    """
    학습 상태 저장 함수 개선
    """
    try:
        # 현재 학습 상태 저장
        state_data = {
            'current_index': current_index,
            'timestamp': time.time(),
            'total_rows': len(df),
            'progress': f"{current_index}/{len(df)}",
            'last_sentence': df.iloc[current_index]['english'] if current_index < len(df) else ""
        }
        
        # 파일 저장
        save_path = TEMP_DIR / 'learning_state.json'
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, ensure_ascii=False, indent=2)
            
        st.success(f"학습 상태가 저장되었습니다. (진행률: {state_data['progress']})")
        
        # 세션 상태 업데이트
        session_state.saved_index = current_index
        session_state.has_saved_state = True
        
        return True
        
    except Exception as e:
        st.error(f"저장 중 오류 발생: {str(e)}")
        return False

def load_learning_state():
    """
    학습 상태 불러오기 함수 개선
    """
    try:
        save_path = TEMP_DIR / 'learning_state.json'
        
        if not save_path.exists():
            return None
            
        with open(save_path, 'r', encoding='utf-8') as f:
            state_data = json.load(f)
            
        # 저장된 데이터 검증
        required_keys = ['current_index', 'timestamp', 'total_rows']
        if not all(key in state_data for key in required_keys):
            st.warning("저장된 상태 데이터가 유효하지 않습니다.")
            return None
            
        return state_data
        
    except Exception as e:
        st.error(f"상태 불러오기 중 오류 발생: {str(e)}")
        return None

def handle_resume_learning(df):
    """
    학습 재개 처리 함수
    """
    try:
        state_data = load_learning_state()
        if state_data is None:
            return 0
            
        # 저장된 상태와 현재 데이터 검증
        if state_data['total_rows'] != len(df):
            st.warning("저장된 데이터의 크기가 현재 데이터와 다릅니다.")
            return 0
            
        current_index = state_data['current_index']
        if 0 <= current_index < len(df):
            st.success(f"이전 학습 상태를 불러왔습니다. (진행률: {current_index}/{len(df)})")
            return current_index
        else:
            st.warning("유효하지 않은 인덱스입니다.")
            return 0
            
    except Exception as e:
        st.error(f"학습 재개 중 오류 발생: {str(e)}")
        return 0

# 음성 선택 변경 시 즉시 설정을 저장하는 함수 추가
def save_voice_settings(settings):
    """음성 설정을 즉시 저장"""
    try:
        # 현재 설정 파일 읽기
        if SETTINGS_PATH.exists():
            with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
                current_settings = json.load(f)
        else:
            current_settings = {}
        
        # 음성 관련 설정 업데이트
        current_settings.update({
            'eng_voice': settings['eng_voice'],
            'kor_voice': settings['kor_voice'],
            'zh_voice': settings['zh_voice'],
            'jp_voice': settings['jp_voice'],
            'vi_voice': settings['vi_voice']
        })
        
        # 설정 파일 저장
        with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(current_settings, f, ensure_ascii=False, indent=2)
            
        return True
    except Exception as e:
        st.error(f"음성 설정 저장 중 오류: {e}")
        return False

def custom_subheader(text):
    """커스텀 부제목 스타일"""
    st.markdown(f"""
        <div style="
            color: #00FF00;
            font-size: 1.2em;
            font-weight: bold;
            margin: 1em 0 0.5em 0;
            padding-bottom: 0.3em;
            border-bottom: 2px solid #00FF00;">
            {text}
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

if st.button("설정 초기화"):
    if SETTINGS_PATH.exists():
        os.remove(SETTINGS_PATH)
    st.session_state.clear()
    st.rerun()
