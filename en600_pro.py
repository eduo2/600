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

## streamlit run en600st/en600_st_pro.py

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
        'third_lang': 'chinese',
        'first_repeat': 0,
        'second_repeat': 1,
        'third_repeat': 1,  
        'eng_voice': 'Jenny (US)',  # 국적 표시 추가
        'kor_voice': '선희',
        'zh_voice': '샤오샤오 (여)',  # 기본값을 샤오샤오로 설정
        'jp_voice': 'Nanami',
        'vi_voice': 'HoaiMy',
        'start_row': 1,
        'end_row': 50,
        'selected_sheet': 'en600 : 생활회화 600문장',  # 기본 시트 설정 수정
        'word_delay': 1,
        'spacing': 1.0,          # 기본값 1.0으로 명시
        'subtitle_delay': 1.0,   # 기본값 1.0으로 명시
        'next_sentence_time': 1.0,  # 기본값 1.0으로 명시
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
        'repeat_count': 3,  # 기본값 3으로 변경
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
        'english_color': '#00FF00',  # 다크모드: 초록색, 브라이트모드: 검정색
        'korean_color': '#00FF00',   # 다크모드: 초록색, 브라이트모드: 검정색
        'chinese_color': '#00FF00',  # 다크모드: 초록색, 브라이트모드: 검정색
        'japanese_color': '#00FF00',  # 다크모드: 초록색, 라이트모드: 흰색
        'vietnamese_color': '#00FF00',  # 다크모드: 초록색, 라이트모드: 흰색
        'japanese_speed': 2.0,  # 일본어 배속 기본값 추가
        'vietnamese_font': 'Arial',  # 베트남어 폰트 기본값 추가
        'vietnamese_font_size': 30,
        'vietnamese_speed': 1.2,
        'healing_music': False,
        'healing_duration': 60,  # 힐링뮤직 기본 재생 시간 1분으로 변경
        'voice_notification': True,
        'notification_voice': '선희',  # 기본 알림 음성
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
        
        # 시트 이름 매핑
        sheet_display_names = {
            'Sheet1': 'en600 : 생활회화 600문장',
            'Sheet2': 'travel : 여행영어 810문장'
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
        return ['en600 : 생활회화 600문장']

def get_sheet_name_from_display(display_name):
    """표시용 시트명에서 실제 시트명 추출"""
    # 시트 이름 역매핑
    sheet_name_mapping = {
        'en600 : 생활회화 600문장': 'Sheet1',
        'travel : 여행영어 810문장': 'Sheet2'
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

# 음성 매핑에 남성 음성 추가
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
        "샤오샤오 (여)": "zh-CN-XiaoXiaoNeural",      # 중국 여성
        "샤오이 (여)": "zh-CN-XiaoYiNeural",          # 중국 여성
        "샤오한 (여)": "zh-CN-XiaoHanNeural",         # 중국 여성
        # 남성 음성
        "윈지엔 (남)": "zh-CN-YunjianNeural",        # 중국 남성
        "윈양 (남)": "zh-CN-YunyangNeural"           # 중국 남성
    },
    'japanese': {
        "Nanami": "ja-JP-NanamiNeural",
        "Keita": "ja-JP-KeitaNeural",
    },
    'vietnamese': {
        "HoaiMy": "vi-VN-HoaiMyNeural",  # 여성 음성
        "NamMinh": "vi-VN-NamMinhNeural"  # 남성 음성
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
        st.session_state.settings_backup = None  # 설정 백업용 변수 추가
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
        st.session_state.settings = {
            'first_lang': 'korean',
            'second_lang': 'english',
            'third_lang': 'chinese',
            'first_repeat': 0,
            'second_repeat': 1,
            'third_repeat': 1,  
            'eng_voice': 'Jenny (US)',  # 국적 표시 추가
            'kor_voice': '선희',
            'zh_voice': '샤오샤오 (여)',  # 기본값을 샤오샤오로 설정
            'jp_voice': 'Nanami',
            'vi_voice': 'HoaiMy',
            'start_row': 1,
            'end_row': 50,
            'selected_sheet': 'en600 : 생활회화 600문장',  # 기본 시트 설정 수정
            'word_delay': 1,
            'spacing': 1.0,          # 기본값 1.0으로 명시
            'subtitle_delay': 1.0,   # 기본값 1.0으로 명시
            'next_sentence_time': 1.0,  # 기본값 1.0으로 명시
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
            'repeat_count': 3,  # 기본값 3으로 변경
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
            'english_color': '#00FF00',  # 다크모드: 초록색, 브라이트모드: 검정색
            'korean_color': '#00FF00',   # 다크모드: 초록색, 브라이트모드: 검정색
            'chinese_color': '#00FF00',  # 다크모드: 초록색, 브라이트모드: 검정색
            'japanese_color': '#00FF00' if is_dark_mode else '#FFFFFF',  # 다크모드: 초록색, 라이트모드: 흰색
            'vietnamese_color': '#00FF00' if is_dark_mode else '#FFFFFF',  # 다크모드: 초록색, 라이트모드: 흰색
            'japanese_speed': 2.0,  # 일본어 배속 기본값 추가
            'vietnamese_font': 'Arial',  # 베트남어 폰트 기본값 추가
            'vietnamese_font_size': 30,
            'vietnamese_speed': 1.2,
            'healing_music': False,
            'healing_duration': 60,  # 힐링뮤직 기본 재생 시간 1분으로 변경
            'voice_notification': True,
            'notification_voice': '선희',  # 기본 알림 음성
        }

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
    settings = st.session_state.settings.copy()
    
    # 설정 백업 복원 (취소 시 사용)
    if return_to_learning and 'settings_backup' in st.session_state:
        settings = st.session_state.settings_backup.copy()
    else:
        settings = st.session_state.settings.copy()

    if return_to_learning:
        # 학습 중 설정 모드 - 간소화된 UI
        st.subheader("학습 설정")
        
        # 시트 선택 옵션 추가
        sheet_names = get_excel_sheets()
        current_sheet_display = settings.get('selected_sheet', sheet_names[0])
        if current_sheet_display not in sheet_names:
            current_sheet_display = sheet_names[0]

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
                settings['selected_sheet'] = selected_sheet  # 실제 시트명만 저장
                settings['start_row'] = 1
                settings['end_row'] = last_row  # 전체 행 수로 설정
                st.info(f"시트 변경: 행 범위가 자동으로 조정. (1-{last_row})")

        # 선택된 시트의 행 수 표시
        try:
            df, last_row = read_excel_data(selected_sheet)
            if df is not None and last_row > 0:
                st.info(f"선택된 시트의 총 행 수: {last_row}")
                
                # 시작 행과 종료 행 설정
                settings['start_row'] = st.number_input(
                    "시작 행",
                    min_value=1,
                    max_value=last_row,
                    value=min(settings.get('start_row', 1), last_row),
                    key="start_row_input"
                )
                
                settings['end_row'] = st.number_input(
                    "종료 행",
                    min_value=1,  # 최소값을 1로 설정하여 시작 행과 무관하게 입력 가능
                    max_value=last_row,
                    value=min(settings.get('end_row', last_row), last_row),
                    key="end_row_input"
                )
        except Exception as e:
            st.error(f"시트 정보 읽기 오류: {e}")
    else:
        # 기본 설정 모드 - 전체 UI
        # 다크 모드 감지
        is_dark_mode = st.get_option("theme.base") == "dark"
        
        # 현재 설정 가져오기
        settings = st.session_state.settings
        
        # 테마가 변경되었을 때 색상 자동 업데이트
        if is_dark_mode:
            if settings['korean_color'] == '#000000':  # 이전에 브라이트 모드였다면
                settings.update({
                    'english_color': '#00FF00',   # 초록색
                    'korean_color': '#FFFFFF',    # 흰색
                    'chinese_color': '#00FF00',   # 초록색
                    'japanese_color': '#00FF00',
                    'vietnamese_color': '#00FF00',
                })
        else:
            if settings['korean_color'] == '#FFFFFF':  # 이전에 다크 모드였다면
                settings.update({
                    'english_color': '#000000',   # 검정색
                    'korean_color': '#000000',    # 검정색
                    'chinese_color': '#000000',   # 검정색
                    'japanese_color': '#FFFFFF',
                    'vietnamese_color': '#FFFFFF',
                })

        # 부제목 스타일 CSS 추가
        st.markdown("""
            <style>
                /* 부제목(subheader) 스타일 */
                .custom-subheader {
                    font-size: 1.3rem !important;
                    font-weight: 600 !important;
                    margin-top: 1.5rem !important;
                    margin-bottom: 1rem !important;
                    color: #00FF7F !important;  /* 스프링그린 색상 */
                    padding: 0.2rem 0;
                    border-bottom: 2px solid #00FF7F;
                }
            </style>
        """, unsafe_allow_html=True)

        # 부제목 커스텀 함수
        def custom_subheader(text):
            st.markdown(f'<div class="custom-subheader">{text}</div>', unsafe_allow_html=True)

        # 기존 subheader 대신 custom_subheader 사용
        custom_subheader("엑셀 시트 설정")
        sheet_names = get_excel_sheets()
        current_sheet_display = settings.get('selected_sheet', sheet_names[0])
        if current_sheet_display not in sheet_names:
            current_sheet_display = sheet_names[0]
        
        col1, col2 = st.columns(2)
        with col1:
            # 시트 선택
            selected_sheet_display = st.selectbox(
                "학습할 시트 선택",
                options=sheet_names,
                index=sheet_names.index(current_sheet_display),
                key="sheet_select_main"
            )
            
            # 실제 시트명 추출
            selected_sheet = get_sheet_name_from_display(selected_sheet_display)
            
            # 시트가 변경되었을 때
            if selected_sheet != get_sheet_name_from_display(settings['selected_sheet']):
                df, last_row = read_excel_data(selected_sheet)
                if df is not None:
                    settings['selected_sheet'] = selected_sheet_display  # 행 수 정보를 포함한 전체 표시명 저장
                    settings['start_row'] = 1
                    settings['end_row'] = min(50, last_row)  # 기본값은 50행 또는 마지막 행
                    st.info(f"시트 변경: 행 범위가 자동으로 조정. (1-{settings['end_row']})")
            
            # 선택된 시트의 행 수 표시
            try:
                df, last_row = read_excel_data(selected_sheet)
                if df is not None:
                    st.info(f"선택된 시트의 총 행 수: {last_row}")
            except Exception as e:
                st.error(f"시트 정보 읽기 오류: {e}")
        
        with col2:
            # 시작 행과 종료 행 설정
            df, last_row = read_excel_data(settings['selected_sheet'])
            if df is not None:
                settings['start_row'] = st.number_input(
                    "시작 행",
                    min_value=1,
                    max_value=last_row,
                    value=min(settings['start_row'], last_row),
                    key="start_row_input"
                )
                
                settings['end_row'] = st.number_input(
                    "종료 행",
                    min_value=1,  # 최소값을 1로 설정하여 시작 행과 무관하게 입력 가능
                    max_value=last_row,
                    value=min(settings['end_row'], last_row),
                    key="end_row_input"
                )

        # CSS 스타일 추가 (다크 모드 대응)
        st.markdown("""
            <style>
                /* 기본 텍스트 색상 */
                .st-emotion-cache-1v0mbdj {
                    color: white !important;
                }
                
                /* 제목 (h1) 폰트 크기 및 색상 조정 */
                .st-emotion-cache-10trblm {
                    font-size: 1.5rem !important;
                    margin-bottom: 0px !important;
                    color: white !important;
                }
                
                /* 부제목 (h2) 폰트 크기 및 색상 조정 */
                .st-emotion-cache-1629p8f h2 {
                    font-size: 1.2rem !important;
                    margin-top: 1rem !important;
                    margin-bottom: 0.5rem !important;
                    color: white !important;
                }
                
                /* 입력 필드 레이블 색상 */
                .st-emotion-cache-1a7c8b8 {
                    color: white !important;
                }
                
                /* 체크박스 및 라디오 버튼 색상 */
                .st-emotion-cache-1a7c8b8 label {
                    color: white !important;
                }
                
                /* 숫자 입력 필드 스타일 */
                div[data-testid="stNumberInput"] {
                    max-width: 150px;
                }
                
                /* 숫자 입력 필드 레이블 스타일 */
                div[data-testid="stNumberInput"] label {
                    font-size: 15px !important;
                    color: white !important;
                }
                
                /* 숫자 입력 필드 입력창 스타일 */
                div[data-testid="stNumberInput"] input {
                    font-size: 15px !important;
                    padding: 4px 8px !important;
                    color: white !important;
                    background-color: #1E1E1E !important;
                }
                
                /* 셀렉트 박스 스타일 */
                div[data-testid="stSelectbox"] label {
                    color: white !important;
                }
                
                /* 셀렉트 박스 입력창 스타일 */
                div[data-testid="stSelectbox"] select {
                    color: white !important;
                    background-color: #1E1E1E !important;
                }
                
                /* 체크박스 스타일 */
                div[data-testid="stCheckbox"] label {
                    color: white !important;
                }
                
                /* 색상 선택기 스타일 */
                div[data-testid="stColorPicker"] label {
                    color: white !important;
                }
            </style>
        """, unsafe_allow_html=True)
        
        settings = st.session_state.settings
        col1, col2 = st.columns([0.7, 0.3])
        with col1:
            st.markdown('<h1 style="font-size: 1.5rem; color: #00FF00;">도파민 대충영어 : 2배 한국어</h1>', unsafe_allow_html=True)
        with col2:
            # 엑셀 파일에서 최대 행 수 가져오기
            try:
                df = pd.read_excel(
                    EXCEL_PATH,
                    header=None,
                    engine='openpyxl'
                )
                max_row = len(df)
            except Exception as e:
                st.error(f"엑셀 파일 읽기 오류: {e}")
                return
            
            # 학습 시작 버튼 (첫 화면에서만 표시)
            if st.button("▶️ 학습 시작", use_container_width=True, key="start_btn"):
                # 시작행과 종료행 검증
                try:
                    df, last_row = read_excel_data(settings['selected_sheet'])
                    if df is None:
                        st.error("엑셀 파일을 읽을 수 없습니다.")
                        return
                    
                    # 행 범위 검증
                    start_row = settings['start_row']
                    end_row = settings['end_row']
                    
                    if start_row < 1 or end_row < 1:
                        st.error("시작행과 종료행은 1 이상이어야 합니다.")
                        return
                    
                    if start_row > end_row:
                        st.error("시작행은 종료행보다 작거나 같아야 합니다.")
                        return
                    
                    if end_row > last_row:
                        st.error(f"종료행이 시트의 총 행 수({last_row})를 초과할 수 없습니다.")
                        return
                    
                    # 모든 검증 통과 시 학습 시작
                    st.session_state.page = 'learning'
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"오류 발생: {e}")
                    return

        # 학습 시작 버튼 스타일
        st.markdown("""
            <style>
                /* 학습 시작/종료 버튼 스타일 */
                div[data-testid="stButton"] > button {
                    width: 100% !important;
                    height: 3em !important;
                    font-size: 1.2rem !important;
                }
            </style>
        """, unsafe_allow_html=True)

        # 언어 순서 설정 섹션의 제목 수정
        custom_subheader("자막 · 음성 · 속도")
        col1, col2, col3 = st.columns(3)
        with col1:
            settings['first_lang'] = st.selectbox("1순위 언어",
                options=['korean', 'english', 'chinese', 'japanese', 'vietnamese'],
                index=['korean', 'english', 'chinese', 'japanese', 'vietnamese'].index(settings['first_lang']),
                format_func=lambda x: LANG_DISPLAY[x],
                key="settings_first_lang")
            
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
            
            # 음성 재생 횟수 설정 추가
            settings['first_repeat'] = st.selectbox("재생 횟수",
                options=list(range(0, 3)),  # 02회
                index=settings.get('first_repeat', 0),
                key="first_repeat")
            
            # 배속 설정 추가
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

        with col2:
            settings['second_lang'] = st.selectbox("2순위 언어",
                options=['korean', 'english', 'chinese', 'japanese', 'vietnamese'],
                index=['korean', 'english', 'chinese', 'japanese', 'vietnamese'].index(settings['second_lang']),
                format_func=lambda x: LANG_DISPLAY[x],
                key="settings_second_lang")
            
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
            
            # 음성 재생 횟수 설정 추가
            settings['second_repeat'] = st.selectbox("재생 횟수",
                options=list(range(0, 3)),  # 0-5회
                index=settings.get('second_repeat', 1),
                key="second_repeat")
            
            # 배속 설정 추가
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

        with col3:
            settings['third_lang'] = st.selectbox("3순위 언어",
                options=['korean', 'english', 'chinese', 'japanese', 'vietnamese'],
                index=['korean', 'english', 'chinese', 'japanese', 'vietnamese'].index(settings['third_lang']),
                format_func=lambda x: LANG_DISPLAY[x],
                key="settings_third_lang")
            
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
            
            # 음성 재생 횟수 설정 추가
            settings['third_repeat'] = st.selectbox("재생 횟수",
                options=list(range(0, 3)),  # 0-5회
                index=settings.get('third_repeat', 1),
                key="third_repeat")
            
            # 배속 설정 추가
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

        # 문장 재생 설정
        custom_subheader("문장 재생")
        col1, col2, col3, col4 = st.columns(4)
        
        # 0.1초부터 2초까지 0.1초 간격의 옵션 생성
        time_options = [round(x * 0.1, 1) for x in range(1, 21)]  # 0.1-2.0초
        
        with col1:
            current_spacing = round(float(settings.get('spacing', 1.0)), 1)  # 기본값 1.0
            current_spacing = max(0.1, min(current_spacing, 2.0))
            try:
                spacing_index = time_options.index(current_spacing)
            except ValueError:
                spacing_index = time_options.index(1.0)  # 기본값 1.0초
            settings['spacing'] = st.selectbox("문장 간격(초)",
                                            options=time_options,
                                            index=spacing_index,
                                            key="spacing")

        with col2:
            current_delay = round(float(settings.get('subtitle_delay', 1.0)), 1)  # 기본값 1.0
            current_delay = max(0.1, min(current_delay, 2.0))
            try:
                delay_index = time_options.index(current_delay)
            except ValueError:
                delay_index = time_options.index(1.0)  # 기본값 1.0초
            settings['subtitle_delay'] = st.selectbox("자막 딜레이(초)",
                                                   options=time_options,
                                                   index=delay_index,
                                                   key="subtitle_delay")

        with col3:
            current_next = round(float(settings.get('next_sentence_time', 1.0)), 1)  # 기본값 1.0
            current_next = max(0.1, min(current_next, 2.0))
            try:
                next_index = time_options.index(current_next)
            except ValueError:
                next_index = time_options.index(1.0)  # 기본값 1.0초
            settings['next_sentence_time'] = st.selectbox("다음 문장(초)",
                                                       options=time_options,
                                                       index=next_index,
                                                       key="next_sentence_time")

        with col4:
            settings['break_interval'] = st.selectbox("브레이크 문장",
                                                  options=['없음', '5', '10', '15', '20'],
                                                  index=0 if not settings.get('break_enabled', True) else 
                                                        ['없음', '5', '10', '15', '20'].index(str(settings.get('break_interval', 10))),
                                                  key="break_interval_input")
            settings['break_enabled'] = settings['break_interval'] != '없음'
            if settings['break_enabled']:
                settings['break_interval'] = int(settings['break_interval'])

        # 자막 숨김 옵션을 한 줄로 배치하고 자막 유지 모드를 첫 번째로 이동
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            settings['keep_subtitles'] = st.checkbox("자막유지 모드",
                                                  value=settings.get('keep_subtitles', True),
                                                  key="keep_subtitles_checkbox")
        with col2:
            hide_first = st.checkbox("1순위 자막 숨김",
                                   value=settings['hide_subtitles']['first_lang'],
                                   key="first_hide")
        with col3:
            hide_second = st.checkbox("2순위 자막 숨김",
                                    value=settings['hide_subtitles']['second_lang'],
                                    key="second_hide")
        with col4:
            hide_third = st.checkbox("3순위 자막 숨김",
                                   value=settings['hide_subtitles']['third_lang'],
                                   key="third_hide")

        # 폰트 및 색상 설정 섹션의 제목 수정
        custom_subheader("폰트 크기 · 색깔")  # 구분자를 '|'에서 '·'로 변경
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            settings['korean_font_size'] = st.number_input("한글",
                                                        value=settings['korean_font_size'],
                                                        min_value=10,
                                                        max_value=50,
                                                        step=1,
                                                        key="korean_font_size_learning")
            default_color = 'green'  # 기본값을 초록색으로 변경
            selected_color = st.selectbox("한글",
                                        options=list(COLOR_MAPPING.keys()),
                                        index=list(COLOR_MAPPING.keys()).index(default_color),
                                        key="korean_color_select")
            settings['korean_color'] = COLOR_MAPPING[selected_color]

        with col2:
            settings['english_font_size'] = st.number_input("영어",
                                                        value=settings['english_font_size'],
                                                        min_value=10,
                                                        max_value=50,
                                                        step=1,
                                                        key="english_font_size_learning")
            default_color = 'green'  # 기본값을 초록색으로 변경
            selected_color = st.selectbox("영어",
                                        options=list(COLOR_MAPPING.keys()),
                                        index=list(COLOR_MAPPING.keys()).index(default_color),
                                        key="english_color_select")
            settings['english_color'] = COLOR_MAPPING[selected_color]

        with col3:
            settings['chinese_font_size'] = st.number_input("중국어",
                                                        value=settings['chinese_font_size'],
                                                        min_value=10,
                                                        max_value=50,
                                                        step=1,
                                                        key="chinese_font_size_learning")
            default_color = 'green'  # 기본값을 초록색으로 변경
            selected_color = st.selectbox("중국어",
                                        options=list(COLOR_MAPPING.keys()),
                                        index=list(COLOR_MAPPING.keys()).index(default_color),
                                        key="chinese_color_select")
            settings['chinese_color'] = COLOR_MAPPING[selected_color]

        with col4:
            settings['japanese_font_size'] = st.number_input("일본어",
                                                        value=settings['japanese_font_size'],
                                                        min_value=10,
                                                        max_value=50,
                                                        step=1,
                                                        key="japanese_font_size_learning")
            default_color = 'green' if st.get_option("theme.base") == "dark" else 'white'
            selected_color = st.selectbox("일본어",
                                        options=list(COLOR_MAPPING.keys()),
                                        index=list(COLOR_MAPPING.keys()).index(default_color),
                                        key="japanese_color_select")
            settings['japanese_color'] = COLOR_MAPPING[selected_color]

        with col5:
            settings['vietnamese_font_size'] = st.number_input("베트남어",
                                                        value=settings['vietnamese_font_size'],
                                                        min_value=10,
                                                        max_value=50,
                                                        step=1,
                                                        key="vietnamese_font_size_learning")
            default_color = 'green' if st.get_option("theme.base") == "dark" else 'white'
            selected_color = st.selectbox("베트남어",
                                          options=list(COLOR_MAPPING.keys()),
                                          index=list(COLOR_MAPPING.keys()).index(default_color),
                                          key="vietnamese_color_select")
            settings['vietnamese_color'] = COLOR_MAPPING[selected_color]

        # 폰트 크기 변경 시 즉시 반영을 위한 CSS 업데이트
        st.markdown(f"""
            <style>
                .english-text {{
                    font-size: {settings['english_font_size']}px !important;
                    color: {settings['english_color']} !important;
                }}
                .korean-text {{
                    font-size: {settings['korean_font_size']}px !important;
                    color: {settings['korean_color']} !important;
                }}
                .chinese-text {{
                    font-size: {settings['chinese_font_size']}px !important;
                    color: {settings['chinese_color']} !important;
                }}
                .japanese-text {{
                    font-size: {settings['japanese_font_size']}px !important;
                    color: {settings['japanese_color']} !important;
                }}
                .vietnamese-text {{
                    font-size: {settings['vietnamese_font_size']}px !important;
                    color: {settings['vietnamese_color']} !important;
                }}
            </style>
        """, unsafe_allow_html=True)

        # 입력 필드에 CSS 클래스 적용
        st.markdown("""
            <style>
                /* 숫자 입력 필드 스타일 */
                div[data-testid="stNumberInput"] {
                    max-width: 150px;
                }
                
                /* 숫자 입력 필드 레이블 스타일 */
                div[data-testid="stNumberInput"] label {
                    font-size: 15px !important;
                }
                
                /* 숫자 입력 필드 입력창 스타일 */
                div[data-testid="stNumberInput"] input {
                    font-size: 15px !important;
                    padding: 4px 8px !important;
                }
            </style>
        """, unsafe_allow_html=True)

        # 저장/취소 버튼
        col1, _ = st.columns([1, 0.2])  # 취소 버튼 컬럼 제거
        with col1:
            if st.button("💾 저장 후 학습 재개", type="primary", key="save_and_resume"):
                if save_settings(settings):  # 설정 저장 성공 시
                    st.session_state.settings = settings.copy()  # 세션 상태 업데이트
                    st.session_state.settings_backup = settings.copy()  # 백업 업데이트
                    st.session_state.page = 'learning'
                    st.rerun()  # 즉시 학습 화면으로 전환

        # 저장/취소 버튼 스타일
        st.markdown("""
            <style>
                /* 저장 버튼 스타일 */
                div[data-testid="stButton"] > button:first-child {
                    background-color: #00FF00 !important;
                    color: black !important;
                }
            </style>
        """, unsafe_allow_html=True)

        # 중국어 음성 선택 부분 수정 (3순위 언어가 중국어일 때)
        if settings['third_lang'] == 'chinese':
            voice_key = 'zh_voice'
            current_voice = settings.get(voice_key)
            
            # 현재 음성이 유효하지 않은 경우 기본값으로 설정
            if not current_voice or current_voice not in VOICE_MAPPING['chinese']:
                current_voice = '샤오샤오 (여)'
                settings[voice_key] = current_voice
            
            # 음성 선택 UI
            new_voice = st.selectbox(
                "음성 선택",
                options=list(VOICE_MAPPING['chinese'].keys()),
                index=list(VOICE_MAPPING['chinese'].keys()).index(current_voice),
                key="chinese_voice_select"
            )
            
            # 음성이 변경되었을 때
            if new_voice != current_voice:
                settings[voice_key] = new_voice
                save_voice_settings(settings)  # 설정 저장
                st.session_state.settings = settings.copy()  # 세션 상태 업데이트
                st.experimental_rerun()

        # 문장 재생 설정 부분 수정
        custom_subheader("학습 설정")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            # 브레이크 설정
            settings['break_enabled'] = st.checkbox(
                "브레이크 사용",
                value=settings.get('break_enabled', True),
                help="설정한 문장 수마다 휴식 시간을 가집니다."
            )
            if settings['break_enabled']:
                settings['break_interval'] = st.selectbox(
                    "브레이크 간격",
                    options=[5, 10, 15, 20],
                    index=[5, 10, 15, 20].index(settings.get('break_interval', 10)),
                    help="몇 문장마다 브레이크를 가질지 설정"
                )
                settings['break_duration'] = st.slider(
                    "브레이크 시간(초)",
                    min_value=5,
                    max_value=30,
                    value=settings.get('break_duration', 10),
                    step=5
                )

        with col2:
            # 자동 반복 설정
            settings['auto_repeat'] = st.checkbox(
                "자동 반복",
                value=settings.get('auto_repeat', True),
                help="학습이 끝나면 자동으로 반복합니다."
            )
            if settings['auto_repeat']:
                settings['repeat_count'] = st.selectbox(
                    "반복 횟수",
                    options=list(range(6)),  # 0-5회
                    index=min(settings.get('repeat_count', 3), 5),
                    format_func=lambda x: f"{x}회",
                    help="총 몇 번 반복할지 설정"
                )

        with col3:
            # 힐링뮤직 설정
            settings['healing_music'] = st.checkbox(
                "힐링뮤직",
                value=settings.get('healing_music', False),
                help="브레이크 타임에 힐링뮤직을 재생합니다."
            )
            if settings['healing_music']:
                col_time1, col_time2 = st.columns(2)
                with col_time1:
                    minutes = st.number_input(
                        "분",
                        min_value=0,
                        max_value=5,
                        value=settings.get('healing_duration', 60) // 60,
                        help="힐링뮤직 재생 시간(분)"
                    )
                with col_time2:
                    seconds = st.number_input(
                        "초",
                        min_value=0,
                        max_value=59,
                        value=settings.get('healing_duration', 60) % 60,
                        help="힐링뮤직 재생 시간(초)"
                    )
                settings['healing_duration'] = minutes * 60 + seconds

        with col4:
            # 음성 알림 설정
            settings['voice_notification'] = st.checkbox(
                "음성 알림",
                value=settings.get('voice_notification', True),
                help="브레이크 시작/종료를 음성으로 알립니다."
            )
            if settings['voice_notification']:
                notification_voices = {
                    '선희 (여)': 'ko-KR-SunHiNeural',
                    '인준 (남)': 'ko-KR-InJoonNeural'
                }
                settings['notification_voice'] = st.selectbox(
                    "알림 음성",
                    options=list(notification_voices.keys()),
                    index=list(notification_voices.keys()).index('선희 (여)' if settings.get('notification_voice') == '선희' else '인준 (남)'),
                    help="알림에 사용할 음성 선택"
                )

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
        ko_speed_text = str(int(ko_speed)) if ko_speed == int(ko_speed) else f"{ko_speed:.1f}"  # 수정
        speed_info.append(f"한글 {ko_speed_text}배")
        
        # 영어 배속 정보
        eng_speed = st.session_state.settings['english_speed']
        eng_speed_text = str(int(eng_speed)) if eng_speed == int(eng_speed) else f"{eng_speed:.1f}"  # 수정
        speed_info.append(f"영어 {eng_speed_text}배")
        
        # 중국어 배속 정보
        zh_speed = st.session_state.settings['chinese_speed']
        zh_speed_text = str(int(zh_speed)) if zh_speed == int(zh_speed) else f"{zh_speed:.1f}"  # 수정
        speed_info.append(f"중국어 {zh_speed_text}배")
        
        # 베트남어 배속 정보
        vn_speed = st.session_state.settings['vietnamese_speed']
        vn_speed_text = str(int(vn_speed)) if vn_speed == int(vn_speed) else f"{vn_speed:.1f}"  # 수정
        speed_info.append(f"베트남어 {vn_speed_text}배")
        
        # 배속 정보를 하나의 문자열로 결합
        speed_display = " · ".join(speed_info)
    
    # 자막을 위한 빈 컨테이너
    subtitles = [st.empty() for _ in range(3)]

    return progress, status, subtitles

async def create_break_audio():
    """브레이크 음성 생성"""
    break_msg = "쉬는 시간입니다, 5초간의 여유를 느껴보세요"
    break_voice = VOICE_MAPPING['korean']['선희']
    audio_file = await create_audio(break_msg, break_voice, 1.0)
    return audio_file

async def start_learning():
    """학습 시작"""
    settings = st.session_state.settings
    sentence_count = 0
    repeat_count = 0  # 현재 반복 횟수
    
    # 엑셀에서 문장 가져오기
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

    while True:
        for i, (eng, kor, chn, jpn, vn) in enumerate(zip(english, korean, chinese, japanese, vietnamese)):
            # 언어별 텍스트와 음성 매핑
            lang_mapping = {
                'korean': {'text': kor, 'voice': VOICE_MAPPING['korean'][settings['kor_voice']], 'speed': settings['korean_speed']},
                'english': {'text': eng, 'voice': VOICE_MAPPING['english'][settings['en_voice']], 'speed': settings['english_speed']},
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

            # 실시간 CSS 업데이트
            st.markdown(f"""
                <style>
                    div[data-testid="stMarkdownContainer"] {{
                        font-size: {settings['korean_font_size']}px !important;
                    }}
                    .korean-text {{
                        color: {settings['korean_color']} !important;
                    }}
                    .english-text {{
                        color: {settings['english_color']} !important;
                    }}
                    .chinese-text {{
                        color: {settings['chinese_color']} !important;
                    }}
                    .japanese-text {{
                        color: {settings['japanese_color']} !important;
                    }}
                    .vietnamese-text {{
                        color: {settings['vietnamese_color']} !important;
                    }}
                </style>
            """, unsafe_allow_html=True)

            # 순위별 자막 표시
            for rank, (lang, repeat) in enumerate([
                (settings['first_lang'], settings['first_repeat']),
                (settings['second_lang'], settings['second_repeat']),
                (settings['third_lang'], settings['third_repeat'])
            ]):
                if not settings['hide_subtitles'][f'{["first", "second", "third"][rank]}_lang']:
                    text = lang_mapping[lang]['text']
                    font = settings.get(f'{lang}_font', 'Arial')
                    color = settings.get(f'{lang}_color', '#00FF00')
                    size = settings.get(f'{lang}_font_size', 28)
                    
                    subtitles[rank].markdown(
                        f'<div class="{lang}-text" style="font-family: {font}; '
                        f'color: {color}; font-size: {size}px;">{text}</div>',
                        unsafe_allow_html=True
                    )

            # 순위별 음성 재생
            for lang, repeat in [
                (settings['first_lang'], settings['first_repeat']),
                (settings['second_lang'], settings['second_repeat']),
                (settings['third_lang'], settings['third_repeat'])
            ]:
                for _ in range(repeat):
                    audio_file = await create_audio(
                        lang_mapping[lang]['text'],
                        lang_mapping[lang]['voice'],
                        lang_mapping[lang]['speed']
                    )
                    if audio_file:
                        # edge-tts로 생성된 파일은 play_audio로 재생
                        play_audio(audio_file)
                        if _ < repeat - 1:
                            await asyncio.sleep(settings['spacing'])
                    elif lang == 'vietnamese':
                        # 베트남어는 create_audio에서 HTML/JS로 바로 재생되므로,
                        # 여기서는 아무것도 하지 않음
                        duration = len(lang_mapping[lang]['text']) * 0.1  # 대략적인 시간
                        await asyncio.sleep(duration)
                        if _ < repeat - 1:
                            await asyncio.sleep(settings['spacing'])

                    else:
                        if _ < repeat - 1:
                            await asyncio.sleep(settings['spacing'])

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
                    break
            
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
        index=['korean', 'english', 'chinese', 'japanese', 'vietnamese'].index(st.session_state.user_language))

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
    elif st.session_state.user_language == 'vietnamese':
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
        # 설정 파일 저장 전 백업 생성
        if SETTINGS_PATH.exists():
            backup_path = SETTINGS_PATH.with_suffix('.json.bak')
            import shutil
            shutil.copy2(SETTINGS_PATH, backup_path)
        
        # 새로운 설정 저장
        with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
            
        # 성공적으로 저장되었는지 확인
        if SETTINGS_PATH.exists():
            return True
    except Exception as e:
        st.error(f"설정 저장 중 오류: {e}")
        # 오류 발생 시 백업에서 복구 시도
        try:
            backup_path = SETTINGS_PATH.with_suffix('.json.bak')
            if backup_path.exists():
                import shutil
                shutil.copy2(backup_path, SETTINGS_PATH)
                st.warning("백업에서 설정을 복구했습니다.")
        except Exception as backup_error:
            st.error(f"백업 복구 중 오류: {backup_error}")
        return False
    return True

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

def play_audio(file_path, sentence_interval=1.0, next_sentence=False):
    """
    음성 파일 재생 - 문장 간격 및 다음 문장 설정 적용
    """
    try:
        if not file_path or not os.path.exists(file_path):
            st.error(f"파일 경로 오류: {file_path}")
            return

        # WAV 파일에서 실제 재생 시간 계산
        try:
            with wave.open(file_path, 'rb') as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()
                duration = frames / float(rate)
        except Exception:
            with open(file_path, 'rb') as f:
                audio_bytes = f.read()
            duration = len(audio_bytes) / 32000

        # 파일을 바이트로 읽기
        with open(file_path, 'rb') as f:
            audio_bytes = f.read()
        audio_base64 = base64.b64encode(audio_bytes).decode()

        # 고유한 ID 생성
        audio_id = f"audio_{int(time.time() * 1000)}"
        
        # HTML 오디오 요소 생성
        st.markdown(f"""
            <audio id="{audio_id}" autoplay="true">
                <source src="data:audio/wav;base64,{audio_base64}" type="audio/wav">
            </audio>
            <script>
                (function() {{
                    const audio = document.getElementById("{audio_id}");
                    
                    // 이전 오디오가 있으면 정지
                    if (window.currentAudio && window.currentAudio !== audio) {{
                        window.currentAudio.pause();
                        window.currentAudio.currentTime = 0;
                        window.currentAudio.remove();
                    }}
                    
                    // 현재 오디오를 전역 변수에 저장
                    window.currentAudio = audio;
                    window.audioEnded = false;
                    
                    // 재생 완료 이벤트
                    audio.onended = function() {{
                        window.audioEnded = true;
                        if (window.currentAudio === audio) {{
                            window.currentAudio = null;
                        }}
                        audio.remove();
                    }};

                    // 재생 시작 이벤트
                    audio.onplay = function() {{
                        window.audioEnded = false;
                    }};
                }})();
            </script>
        """, unsafe_allow_html=True)

        # 대기 시간 계산
        if next_sentence:
            # 다음 문장으로 빠르게 넘어가기
            wait_time = duration + 0.3  # 최소 대기 시간
        else:
            # 문장 간격 적용
            base_wait = duration
            
            # 긴 문장에 대한 추가 대기 시간
            if duration > 5:
                extra_wait = duration * 0.1  # 10% 추가
            else:
                extra_wait = 0.5
                
            # 사용자가 설정한 문장 간격 적용
            wait_time = base_wait + extra_wait + sentence_interval

        # 최소 대기 시간 보장
        wait_time = max(wait_time, duration + 0.3)
        
        time.sleep(wait_time)

    except Exception as e:
        st.error(f"음성 재생 오류: {str(e)}")
    finally:
        # 임시 파일 삭제
        try:
            if file_path and TEMP_DIR in Path(file_path).parents:
                os.remove(file_path)
        except Exception:
            pass

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

if __name__ == "__main__":
    main()