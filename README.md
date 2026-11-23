# 오늘의 음악 (Today's Music App)

시간 · 날씨 · 지금 기분 · 내게 필요한 것 · 장르를 기반으로 음악을 추천하고,
SQLite 데이터베이스와 MusicBrainz 공개 API를 연동해 매번 새로운 곡을 추천하는 모바일 웹 앱입니다.

## 실행 방법

1. 패키지 설치
   ```bash
   pip install -r backend/requirements.txt
   ```

2. 서버 실행
   ```bash
   uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
   ```

3. 브라우저 또는 스마트폰에서 접속
   - `http://localhost:8000`
   - 같은 Wi-Fi의 스마트폰에서 접속하려면 PC의 로컬 IP(`http://192.168.x.x:8000`)로 접속한 뒤 "홈 화면에 추가"를 누르면 앱처럼 사용할 수 있습니다.
