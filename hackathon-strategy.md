# 🏆 AfterCare — Pierwszy AI agent follow-up dla polskich szpitali

### "W USA to unicorn za $1.64B. W Polsce właśnie weszło prawo. Nikt tu tego nie robi. My zaczynamy."

---

## PROBLEM — TWARDE DANE

### Globalnie (udowodnione):
- **~20% pacjentów** wraca do szpitala w ciągu 30 dni od wypisu
- **27%** tych readmisji jest ZAPOBIEGALNE
- **20%** pacjentów doświadcza zdarzeń niepożądanych po wypisie
- Najczęściej: **błędy w lekach** (40% callerów w badaniach miało problem z lekami)
- Proste **telefony follow-up zmniejszają readmisje o 21-23%** (meta-analizy, wielokrotnie potwierdzone)

### W Polsce:
- **Prawie co piąty** hospitalizowany wraca w ciągu 30 dni (PAP/Harvard)
- Szpitale **zaniżają statystyki** — liczą tylko ten sam oddział + ta sama diagnoza = ~2%. Realnie to 15-20%.
- Leczenie szpitalne w 2025: **97,25 mld zł** (NFZ). Nawet 5% readmisji to **~5 mld zł** potencjalnych oszczędności
- **Brak systemowego follow-up** po wypisie — pielęgniarki nie dzwonią, POZ nie ogarnia
- Średni koszt leczenia pacjenta: **5 250 zł/rok** (2024), rośnie

### GAME CHANGER: Nowe prawo

**Ustawa o jakości w opiece zdrowotnej** (16.06.2023) + **Rozporządzenie MZ ws. wskaźników jakości** (10.09.2024, Dz.U. 2024 poz. 1349):

- NFZ MUSI monitorować wskaźniki jakości szpitali (Art. 5)
- Wskaźniki obejmują **częstość rehospitalizacji** (niewydolność serca — 30 dni, psychiatria — 14/28 dni)
- NFZ BĘDZIE **publicznie publikował** wyniki szpitali (BIP, do 30 kwietnia)
- Art. 5 ust. 3: **Rozliczanie świadczeń w oparciu o wskaźniki jakości** — czyli pieniądze zależą od jakości
- Szpitale MUSZĄ mieć wewnętrzny system zarządzania jakością (od 30.06.2024)
- Autoryzacja szpitali (warunek kontraktu z NFZ) wymaga spełnienia standardów jakości

**To jest polski HRRP. Właśnie się zaczyna. Szpitale potrzebują narzędzi. NIKT im ich nie daje.**

---

## ROZWIĄZANIE: AfterCare

Agent AI dzwoni do pacjentów 48h po wypisie, sprawdza: leki, objawy, zrozumienie zaleceń, samopoczucie. Eskaluje problemy do zespołu medycznego. Generuje raport jakościowy.

### Flow (perspektywa pacjenta):

📞 Agent dzwoni 48h po wypisie (Vapi outbound)

🤖 *"Dzień dobry, panie Kowalski. Dzwonię ze Szpitala Miejskiego w sprawie Pana pobytu. Chcemy się upewnić że wszystko w porządku po wypisie. Czy ma Pan chwilę?"*

👴 *"Tak... wie Pan, te leki co mi dali to nie bardzo wiem który kiedy brać."*

🤖 Agent wykrywa **zamęt** w głosie (Gemini affective) → przełącza na **Medication Agent** (Vapi Squad handoff)

🤖 *"Rozumiem, to ważne żeby leki brać prawidłowo. Zaraz Panu pomogę. Czy ma Pan te leki gdzieś pod ręką?"*

👴 *"Tak, leżą tu na stole."*

🤖 *"Świetnie. Wysyłam Panu SMS-a z linkiem. Proszę go kliknąć i zrobić zdjęcie tych leków — a ja Panu powiem czy wszystko się zgadza."*

→ **Function call** → SMS przychodzi na telefon pacjenta:

> 📱 **SMS od AfterCare / Szpital Miejski:**
> *"Proszę kliknąć link i zrobić zdjęcie swoich leków:*
> *aftercare.pl/foto/k7x9m2*
> *Zdjęcie pomoże nam sprawdzić czy ma Pan wszystkie przepisane leki."*

👴 Pacjent klika link → otwiera się prosta strona z przyciskiem "Zrób zdjęcie" → robi zdjęcie opakowań leków na stole → klik "Wyślij"

→ Zdjęcie trafia na backend → **Gemini Vision API** analizuje w ~3 sekundy
→ Rozpoznaje: Paracetamol 500mg, Enoxaparyna 40mg
→ Porównuje z kartą wypisu: oczekiwane 3 leki, znalezione 2 → **brakuje Omeprazol**

🤖 *"Dziękuję za zdjęcie. Widzę Paracetamol i Enoxaparynę — to się zgadza. Ale na zdjęciu nie widzę Omeprazolu, który też był przepisany. Czy Pan go wykupił?"*

👴 *"A, ten na żołądek? Chyba nie..."*

🤖 *"To ważny lek — chroni żołądek przed działaniem innych leków. Proszę go wykupić w aptece. Wysyłam SMS-a z pełną listą leków i dawkowaniem."*

→ **Function call** → SMS z harmonogramem:

> 📱 **SMS od AfterCare:**
> *Pana leki po wypisie:*
> *• Paracetamol 500mg — 2x dziennie (rano, wieczorem)*
> *• Enoxaparyna 40mg — 1x dziennie (zastrzyk podskórny)*
> *• ⚠️ Omeprazol 20mg — 1x dziennie (rano, przed jedzeniem) — PROSZĘ WYKUPIĆ*

→ **Function call** → Alert w systemie szpitala: "⚠️ Pacjent Kowalski — brakujący lek: Omeprazol 20mg"
→ **Eskalacja** do pielęgniarki koordynującej jeśli red flag (gorączka, ból w klatce, duszność)

### Co agent robi w trakcie rozmowy:

| Etap | Co robi | Technologia |
|---|---|---|
| Weryfikacja | Potwierdza tożsamość (data urodzenia) | Vapi voice + Gemini |
| Leki | Pyta o każdy lek, porównuje z kartą wypisu | Gemini Pro (reasoning) + document processing |
| Objawy | Structured assessment, red flag detection | Gemini Flash + affective dialog |
| Zrozumienie | Czy pacjent rozumie zalecenia? | Gemini (tone analysis) |
| SMS | Wysyła harmonogram leków w prostym języku | Vapi SMS + Gemini generation |
| Alert | Tworzy wpis w systemie szpitalnym | Vapi function calling |
| Raport | Generuje raport jakościowy per pacjent | Gemini structured output |

---

## DLACZEGO VAPI JEST NIEZASTĄPIONY

| Funkcja Vapi | Po co w AfterCare |
|---|---|
| **Outbound calling at scale** | Agent dzwoni do 100+ pacjentów dziennie — szpital z 500 łóżek wypisuje ~30-50/dzień |
| **Squads** | Triage → Medication → Symptom → Escalation — handoffy mid-call BEZ rozłączania |
| **Function calling** | Sprawdza kartę wypisu, tworzy alert, wysyła SMS, loguje do systemu |
| **SMS bidirectional** | Harmonogram leków, przypomnienia, potwierdzenia wizyt follow-up |
| **Backchanneling** | "Mm-hmm", "rozumiem" — starsi pacjenci MUSZĄ czuć że ktoś słucha |
| **100+ języków** | Pacjenci ukraińskojęzyczni w polskich szpitalach — realne i rosnące |
| **Analytics** | Ile pacjentów miało problem z lekami, ile eskalacji, conversion na follow-up wizyty |

## DLACZEGO GOOGLE MULTIMODAL

| Modalność | Technologia | Zastosowanie |
|---|---|---|
| Audio IN | Gemini Flash via Vapi | Głos pacjenta — rozumie co mówi |
| Affective IN | Gemini affective dialog | Wykrywa zamęt, stres, niepewność w głosie |
| Document IN | Gemini Pro document processing | Czyta kartę wypisu PDF, listę leków |
| Structured IN | Function calling → Gemini context | Historia pacjenta, dane z systemu |
| Audio OUT | Gemini → Vapi TTS | Mówi ciepłym głosem, prowadzi rozmowę |
| Text OUT | Gemini generation | SMS z harmonogramem leków, przypomnienia |
| Structured OUT | Gemini + function calling | Alert, raport jakościowy, wpis do systemu |

---

## COMPETITIVE LANDSCAPE

| | USA | Polska |
|---|---|---|
| Problem | Identyczny (~20% readmisji) | Identyczny, ale UKRYTY przez zaniżone statystyki |
| Regulacja | HRRP od 2012 (dojrzały) | Ustawa o jakości 2023 + rozporządzenie 2024 (ŚWIEŻY!) |
| Kary | Do 3% przychodów Medicare | Rozliczanie wg wskaźników jakości (Art. 5) — nadchodzi |
| Konkurencja | Hippocratic AI ($1.64B), Kaigo, Dimer | **ZERO. NIC. NIKT.** |
| AI adoption | Zaawansowana | Wczesna — ale e-Zdrowie rośnie |
| Szansa | Zajęta przez wielkich graczy | **OTWARTE POLE** |

---

## PITCH NA SCENIE (5 minut)

**:00-:30 — Hook**
"Co piąty pacjent wraca do szpitala w ciągu 30 dni. W USA za rozwiązanie tego problemu Hippocratic AI dostał $278 milionów. W Polsce właśnie weszło prawo które zmusza szpitale do mierzenia jakości. I NIKT nie daje im narzędzi. My to zmieniamy."

**:30-1:30 — Problem**
- Dane: 20% readmisji, 27% zapobiegalne, leki to #1 problem
- Nowe prawo: wskaźniki jakości, NFZ rozlicza, szpitale muszą działać
- Obecna sytuacja: pielęgniarki nie mają czasu dzwonić, formularze papierowe, zero systemu

**1:30-3:30 — LIVE DEMO**
- "Pan Nowak wrócił do domu po operacji. 48 godzin później nasz agent dzwoni."
- Telefon dzwoni NA SCENIE
- Rozmowa: weryfikacja → leki (agent wykrywa brakujący!) → SMS z harmonogramem → alert na dashboardzie
- Dashboard: nowe zgłoszenie, czerwona flaga "brakujący lek: omeprazol"
- Opcjonalnie: juror dzwoni sam do agenta

**3:30-4:30 — Architektura + Dane**
- Multi-agent diagram (ADK + Vapi Squads)
- Google + Vapi stack
- "W USA follow-up call zmniejsza readmisje o 21%. Jedna readmisja kosztuje NFZ średnio 5-12 tys. zł. Szpital z 500 łóżek, 15K wypisów rocznie, 3K readmisji. Zmniejsz o 21% = 630 unikniętych = **3-7.5M zł oszczędności.**"

**4:30-5:00 — Close**
"W USA ten rynek ma unicorna. W Polsce jest pusty. Prawo właśnie weszło. Szpitale MUSZĄ mierzyć jakość, a nie mają narzędzi. AfterCare to nie jest kolejny chatbot. To jest system, który dzwoni, słucha, rozumie, i chroni pacjenta. Bo opieka nie kończy się przy wypisie."

---

## REVENUE MODEL (PL)

**Per-pacjent**: 15-30 zł/follow-up call (vs. koszt pielęgniarki: 50-100 zł/godzinę)
**SaaS per łóżko**: 50-150 zł/łóżko/mies. (szpital 500 łóżek = 25-75K zł/mies.)
**ROI dla szpitala**: 1 uniknięta readmisja = 5-12K zł. 10 unikniętych/mies = 50-120K zł oszczędności.
**Break-even**: szpital płaci 25K/mies, oszczędza 50-120K/mies. ROI: 2-5x.

**Wejście na rynek**: Pilotaż z 2-3 szpitalami. Wyniki → case study → skala.

---

## OBRONA PRZED ATAKAMI JURORÓW

**"To jest Hippocratic AI po polsku"**
→ "Dokładnie. I to jest siła tego pitcha. Hippocratic AI udowodnił że to działa — $278M fundingu, 9/10 patient satisfaction, 30% redukcja readmisji. My bierzemy udowodniony model i wchodzimy na rynek gdzie NIKT tego nie robi, a prawo właśnie wymusza jakość."

**"Polskie szpitale nie mają budżetu na AI"**
→ "Polskie szpitale mają budżet 97 mld zł na leczenie szpitalne. 5% na readmisje = ~5 mld zł. AfterCare kosztuje ułamek tego. A teraz NFZ będzie ROZLICZAŁ jakość — szpitale które nie poprawią wskaźników, stracą pieniądze."

**"Jak wejdziecie do szpitali?"**
→ "Pilotaż z 2-3 szpitalami. Mateusz Chrobok przeszkolił 7000 ludzi w AI. Piotr Nowosielski ma Just Join IT — rekrutacja w szpitalach. W Polsce wszyscy się znają — jeden pilot z wynikami otwiera drzwi."

**"HIPAA/RODO?"**
→ "Vapi deklaruje HIPAA compliance. Gemini na Vertex AI ma BAA. RODO wymaga data processing agreement — standard w SaaS. Na hackathon: mock data. W produkcie: pełna compliance."

**"Czy AI powinien dzwonić do chorych?"**
→ "Agent NIE diagnozuje. NIE leczy. PYTA o leki i objawy — to samo co ankieta wypisu. Wykrywa problemy i ESKALUJE do człowieka. To jest triage, nie diagnoza. Hippocratic AI robi to samo i ma 9/10 patient satisfaction."

**"Gdzie multimodal?"**
→ "Agent DZWONI (voice), CZYTA kartę wypisu (document), SŁYSZY niepewność w głosie (affective), wysyła link SMS-em (text), pacjent robi ZDJĘCIE leków (vision), agent MÓWI co widzi na zdjęciu (vision→voice), wykrywa brakujący lek i tworzy ALERT (structured data). To jest 7 modalności w jednym callu. Na scenie to zobaczycie na żywo."

---

## IMPLEMENTATION PLAN (8h, 5+ osób)

### TEAM SPLIT:

**Osoba 1-2: Vapi Pipeline**
- Konto Vapi, numer PL (Twilio)
- Outbound call setup + system prompts (POLSKI JĘZYK!)
- Vapi Squad: Triage → Medication → Symptom (3 agenty)
- Function calling: check_medications, send_sms, create_alert
- SMS bidirectional
- Test: outbound call → pełny flow → SMS → alert

**Osoba 3: Gemini Backend**
- FastAPI endpoint
- Gemini Pro: document processing (mock karta wypisu PDF)
- Gemini affective: analiza tonu (zmapuj na: spokojny/zaniepokojony/zdezorientowany)
- RAG: lista leków z karty wypisu → porównanie z odpowiedzią pacjenta
- Structured output: raport jakościowy JSON

**Osoba 4: Integracje + Backend**
- Webhook orchestrator (Vapi → Gemini → Vapi)
- Mock system szpitalny (API: pacjent, wypis, leki)
- Alert system
- SMS gateway

**Osoba 5: Dashboard + Demo**
- React dashboard: lista pacjentów, statusy callerów, alerty, raporty
- Widok "wskaźniki jakości" (nawiązanie do rozporządzenia!)
- Live update
- Pitch deck (5-6 slajdów)
- Demo rehearsal x3

**Osoba 6 (jeśli jest): Edge cases + Polish UX**
- Co jeśli pacjent nie odbiera? (retry, SMS fallback)
- Polskie idiomy, naturalny język
- Testy z różnymi scenariuszami (senior, młody, niechętny)
- Backup plan

### ⚠️ FALLBACK
Jeśli multi-agent (Squads) za trudny → jeden agent z function calling. Nadal multimodal, nadal działa, nadal impressive.

---

## DLACZEGO TO WYGRYWA

1. **Innovation**: Udowodniony model z USA ($1.64B unicorn), zero konkurencji w Polsce, nowe prawo wymusza adoption
2. **Running Code**: Dzwonisz na scenie, agent odpowiada po polsku, SMS przychodzi, dashboard się aktualizuje
3. **Real-world Impact**: 20% readmisji, 27% zapobiegalne, follow-up zmniejsza je o 21%. Miliardy złotych
4. **Theme**: Multimodal (voice+document+SMS+affective+structured) AI Agent z Google (Gemini, ADK) & Vapi (Squads, outbound, function calling, SMS)
5. **Business**: Jasny revenue model, ROI 2-5x dla szpitala, regulatory tailwind, pusty rynek
6. **Jury**: Dhruva (healthcare+accessibility+Vapi), Joe (biznes+revenue), Mateusz (agentic+safety), Bogy (investable), Piotr (product), Mike/Michał (tech quality)
