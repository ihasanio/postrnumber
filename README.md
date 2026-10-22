# 7xwon (Bet Exchange Systems) API Dokümantasyonu

**7xwon (`https://7xwon.com/`)** bir **Betfair / Bet Exchange** tarzı (Back / Lay) bahis borsası sistemidir.

- **Resmi Web:** `https://7xwon.com/`
- **Arka Plan REST API:** `https://api.7xwon.com/`
- **Masaüstü Proje Dizini:** `C:\Users\User\Desktop\7xwon_API`

---

## 1. Mimari & Genel Mantık
- LIG111 ve BetRehberi klasik bülten/spor bahisleri iken; **7xwon** bir **Bet Exchange (Back / Lay - Lehine / Aleyhine)** sistemidir.
- Tüm istekler JSON formatında ve `POST` (ya da `GET`) yöntemiyle doğrudan `https://api.7xwon.com/` adresine iletilir.
- Giriş yapıldıktan sonra dönen token `Authorization: Bearer <TOKEN>` başlığı ile taşınır. Giriş yapılmadığında token `"unlogged"` olarak gönderilir.

---

## 2. API Uç Noktaları (Endpoints)

### 2.1. Kimlik Doğrulama & Kullanıcı
- **POST `/login`**
  - **Body:**
    ```json
    {
      "username": "kullanici_adi",
      "password": "sifre",
      "device": "uuid4_veya_device_id",
      "remember": false
    }
    ```
  - **Dönen:** `{ "status": true, "data": { "token": "...", ... } }` veya `{ "status": false, "msg": "..." }`
- **GET `/user`**
  - Giriş yapmış kullanıcının profil, bakiye ve yetkilerini getirir.
- **GET `/logout`**
  - Oturumu sonlandırır.

### 2.2. Canlı ve Bülten Maçları (Events)
- **POST `/main-events`**
  - Token gerekmez (`Bearer unlogged` ile de çalışır).
  - Canlı ve yaklaşan tüm borsa maçlarını, skorlarını, periyotlarını ve eşleşen hacimlerini (`matched`) listeler.
- **POST `/event`**
  - **Body:** `{"id": 36220684}` (Maç ID'si)
  - Maça ait tüm borsa marketlerini (Match Odds, Over/Under, Correct Score vb.), Back (Lehine) ve Lay (Aleyhine) oran ve likidite hacimlerini (`size`) listeler.
- **POST `/countries`** & **POST `/leagues`**
  - Ülke ve lig filtrelerini listeler.

### 2.3. Bahis Oynama (Send Bet / Order)
- **POST `/send`**
  - **Body:**
    ```json
    {
      "eventid": 36220684,
      "market_id": "1.264287378",
      "selection_id": 9470811,
      "handicap": 0,
      "side": "back",
      "amount": 2.0,
      "price": 1.06,
      "co": 0,
      "special": false
    }
    ```
  - **Parametreler:**
    - `side`: `"back"` (Lehine) veya `"lay"` (Aleyhine)
    - `amount`: Oynanacak tutar
    - `price`: İstenen oran

### 2.4. Kupon / Bahis Yönetimi
- **POST `/bets`**
  - Kullanıcının açık ve geçmiş exchange bahislerini getirir (`limit`, `offset`, `status`).
- **POST `/cancel`**
  - **Body:** `{"id": "BAHIS_ID"}`
  - Henüz eşleşmemiş (unmatched) borsa teklifini iptal eder.
