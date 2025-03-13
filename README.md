# Client MQTT v5

  MQTT (Message Queue Telemetry Transport) este un standard de comunicație prin internet, inventat și dezvoltat de IBM în 1999, care definește un protocol de transport al mesajelor prin internet (prin TCP/IP în general), între un server ("message broker") și mai mulți clienți, pe modelul "publicare și abonare" ("publish and subscribe").


  Este un protocol de conectivitate "mașină - mașină" (M2M) / "Internet of Things", conceput a fi simplu și flexibil, cu cerințe minime de resurse, util pentru conexiunile cu locații la distanță și perfect pentru toate tipurile de aplicații IoT, fie că sunt automatizări industriale (IoT) sau automatizări casnice/rezidențiale/de consum (Consumer IoT).

  Este, de asemenea, ideal și pentru aplicații mobile, datorită dimensiunilor mici, consumului redus de energie, pachetelor de date minimizate și distribuției eficiente a informației către unul sau mai mulți receptori.


## Modelul de funcționare cu MQTT

Modelul descris de standardul MQTT funcționează după următoarea secvență de acțiuni:
- Un client se conecteaza la server ("broker") si isi publica mesajele cu o anumita eticheta ("topic");
- Alti clienti se aboneaza ("subscribe") la broker, la anumite topicuri
- Brokerul transmite mai departe mesajele cu un anumit topic clientilor abonati la acel topic.

![MQTT Protocol](https://www.neovasolutions.com/wp-content/uploads/2021/05/Untitled-design-22.png)

## Formatul pachetelor de control

Structura unui pachet de control MQTT este următoarea:
- Fixed Header, care este prezent în toate pachetele de control MQTT. Acesta este format din:
    - Control Packet type. Acesta ocupă primii 4 biți din primul octet al headerului fix. Și conține tipul pachetului de control, despre care vom vorbi în detaliu mai încolo.
    - Flags. Acestea ocupă următorii 4 biți ai primului octet din headerul fix. Aici flag-urile sunt toate rezervate și puse pe 0 în afară de flag-ul de PUBLISH. Care conține DUP(Duplicate delivery of a PUBLISH packet), Qos(PUBLISH Quality of Service) și RETAIN(PUBLISH retained message flag). Când un flag este marcat ca rezervat. Se referă la faptul că este rezervat pentru ultilizare viitoare într-un update al MQTT sau alte utilizări ulterioare. Și din această cauză trebuie setat pe 0, altfel va fi primit ca un pachet malformat. 
    - Remaining Length. Începe de la al doilea octet și aici este stocată lungimea rămasă în octeți în cadrul pachetului de Control curent, incluzând datele din headerul variabil și payload. Lungimea rămasă nu include octeții folosiți pentru a codifica lungimea rămasă. Mărimea pachetului este numărul total de octeți dintr-un pachet de control MQTT, fiind egală cu lungimea headerului fix + lungimea rămasă.
- Variable Header
  - Unele pachete de control MQTT conțin o componentă de header variabil. Acesta se află între headerul fix și payload. Conținutul acestuia depinde în funcție de tipul pachetului. Headerul variabil conține:
      - Packet Identifier. Acesta este folosit de majoritatea pachetelor de control MQTT. Se stochează pe 2 octeți
      - Properties. Acesta este ultimul câmp al headerului variabil de completat. Setul de proprietăți este format din lungimea proprietăților urmat de proprietăți.
      - Propery Length. Include lungimea proprietăților, dacă nu există vreo proprietate lungimea trebuie setată pe 0.
      - Property. Acest câmp este format dintr-un identificator, urmat de o valoare. Dacă un pachet de control conține un identificator care nu este valid pentru tipul lui de pachet sau conține o valoare nespecificată în tipul ăla de dată, atunci se va recunoaște ca un pachet malformat.
- Payload
  - Câteva dintre pachetele de control MQTT conțin ca o parte finală a unui pachet, un payload. Dacă ne referim la un pachet PUBLISH acesta este mesajul aplicației.
- Reason Code
  - Este o valoare naturală care indică rezultatul unei operații. Valori mai mari de 0x80 reprezintă o eroare.
 
## Pachetele de control MQTT

Sunt 15 la număr, și anume:

- CONNECT
  - Descriere:
    - Inițiază o conexiune între un client și broker
  - Fixed Header conține:
      - Tipul pachetului(0x1)
      - Flag-uri(0)
      - Lungimea rămasă
  - Variable Header conține:
      - Numele protocolului(MQTT)
      - Versiune protocol(0x05)
      - Flag-urile pentru Connect(xxxxxxx0)
      - Timerul Keep Alive
      - Proprietăți
  - Payload conține:
      - Identificator client
      - Topic Will(Opțional)
      - Mesaj Will(Opțional)
      - Nume utilizator(Opțional)
      - Parolă(Opțional)
- CONNACK
  - Descriere:
    - Confirmă primirea mesajului CONNECT de către broker
  - Fixed Header conține:
      - Tipul pachetului(0x2)
      - Lungimea rămasă
  - Variable Header conține:
      - Flag-urile pentru Connect Acknowledge(0000000x)
      - Reason code-ul(0x00 - 0x9F)
  - Payload nu există
- PUBLISH
  - Descriere:
    - Trimite un mesaj de la un client către broker pentru a fi distribuit către alte clienți abonați la un anumit subiect
  - Fixed Header conține:
      - Tipul pachetului(0x3)
      - Flag-uri(DUP, QoS, RETAIN)(xxxx)
      - Lungimea rămasă
  - Variable Header conține:
      - Lungimea numelui topicului
      - Numele topicului
      - Identificatorul de pachet(Dacă QoS > 0)
  - Payload conține:
      - Mesajul în sine(de lungime lungime rămasă - lungimea variable header)
- PUBACK
  - Descriere:
    - Confirmă primirea unui mesaj PUBLISH cu QoS 1
  - Fixed Header conține:
      - Tipul pachetului(0x4)
      - Flag-uri(0)
      - Lungimea rămasă
  - Variable Header conține:
      - Identificator pachet
      - Reason Code(0x00 - 0x99)
      - Lungime proprietăți
  - Payload este gol
- PUBREC
  - Descriere:
    - Confirmă primirea unui mesaj PUBLISH cu QoS 2
  - Fixed Header conține:
      - Tipul pachetului(0x5)
      - Flag-uri(0)
      - Lungimea rămasă
  - Variable Header conține:
      - Identificator pachet
      - Reason Code(0x00 - 0x99)
      - Lungime proprietăți
  - Payload este gol
- PUBREL
  - Descriere:
    - Marchează disponibilitatea mesajului pentru confirmare finală la QoS 2
  - Fixed Header conține:
      - Tipul pachetului(0x6)
      - Flag-uri(0010)
      - Lungimea rămasă
  - Variable Header conține:
      - Identificator pachet
      - Reason Code(0x00 - 0x99)
      - Lungime prorietăți
  - Payload este gol
- PUBCOMP
  - Descriere:
    - Confirmă completarea livrării pentru QoS 2
  - Fixed Header conține:
      - Tipul pachetului(0x7)
      - Flag-uri(0)
      - Lungimea rămasă
  - Variable Header conține:
      - Identificator pachet
      - Reason Code(0x00 | 0x92)
      - Lungime proprietăți
  - Payload este gol
- SUBSCRIBE
  - Descriere:
    - Solicită abonarea unui client la unul sau mai multe subiecte
  - Fixed Header conține:
      - Tipul pachetului(0x8)
      - Flag-uri(0010)
      - Lungimea rămasă
  - Variable Header conține:
      - Identificator pachet
      - Lungime proprietăți
  - Payload conține:
      - Lungime topic
      - Mesaj cu topicul
      - OoS-ul care va fi folosit
- SUBACK
  - Descriere:
    - Confirmă primirea mesajului SUBSCRIBE
  - Fixed Header conține:
      - Tipul pachetului(0x9)
      - Flag-uri(0)
      - Lungimea rămasă
  - Variable Header conține:
      - Identificator pachet
  - Payload conține:
      - Cod de returnare(0x00 - 0xA2)
- UNSUBSCRIBE
  - Descriere:
    - Solicită dezabonarea unui client de la unul sau mai multe subiecte
  - Fixed Header conține:
      - Tipul pachetului(0xA)
      - Flag-uri(0010)
      - Lungimea rămasă
  - Variable Header conține:
      - Identificator pachet
      - Lungime proprietăți
  - Payload conține:
      - Lungime topic
      - Topic
- UNSUBACK
  - Descriere:
    - Confirmă primirea mesajului UNSUBSCRIBE
  - Fixed Header conține:
      - Tipul pachetului(0xB)
      - Flag-uri(0)
      - Lungimea rămasă
  - Variable Header conține:
      - Identificator pachet
      - Lungime proprietăți
  - Payload conține:
      - Cod de returnare(0x00 - 0x91)
- PINGREQ
  - Descriere:
    - Menține conexiunea activă între client și broker
  - Fixed Header conține:
      - Tipul pachetului(0xC)
      - Flag-uri(0)
      - Lungimea rămasă(0)
  - Variable Header nu există
  - Payload nu există
- PINGRESP
  - Descriere:
    - Confirmă primirea unui mesaj PINGREQ
  - Fixed Header conține:
      - Tipul pachetului(0xD)
      - Flag-uri(0)
      - Lungime rămasă(0)
  - Variable Header nu există
  - Payload nu există
- DISCONNECT
  - Descriere:
    - Închide conexiunea între client și broker
  - Fixed Header conține:
      - Tipul pachetului(0xE)
      - Flag-uri(0)
      - Lungimea rămasă
  - Variable Header conține:
      - Reason Code(0x00 - 0xA2)
      - Lungime proprietăți
  - Payload nu există
- AUTH
  - Descriere:
    - Gestionează autentificarea suplimentară între client și broker
  - Fixed Header conține:
      - Tipul pachetului(0xF)
      - Flag-uri(0)
      - Lungimea rămasă
  - Variable Header conține:
      - Reason Code(0x00, 0x18, 0x19)
      - Lungime proprietăți
      - Proprietăți
  - Payload nu există

## Sistemul Keep Alive


Mecanismul Keep Alive în MQTT asigură că conexiunea dintre client și broker rămâne activă, chiar și atunci când nu sunt trimise mesaje. Acest lucru este important în aplicațiile IoT, unde dispozitivele pot avea conectivitate intermitentă sau moduri de economisire a energiei.

Cum funcționează:

- Intervalul Keep Alive:
  - Atunci când un client se conectează la broker folosind mesajul CONNECT, acesta specifică un interval Keep Alive în secunde. Acest interval este perioada maximă care poate trece între transmisiunile de   pachete de control ale clientului.
  - Intervalul este negociat la începutul sesiunii și este trimis ca parte din pachetul CONNECT.

- Pachetele PINGREQ și PINGRESP:
  - Pentru a menține conexiunea activă, clientul trebuie să trimită un pachet PINGREQ brokerului dacă nu a trimis alte pachete într-o perioadă de o dată și jumătate mai mare decât intervalul Keep Alive.

  - Când brokerul primește un PINGREQ, răspunde cu un pachet PINGRESP. Acesta semnalează clientului că conexiunea este încă activă și brokerul este disponibil.

- Monitorizarea conexiunii:
  - Atât clientul cât și brokerul folosesc mecanismul Keep Alive pentru a monitoriza conexiunea.
  - Dacă brokerul nu primește niciun pachet (inclusiv PINGREQ) de la client în intervalul Keep Alive, acesta consideră că conexiunea a fost pierdută. De obicei, brokerul închide conexiunea clientului și eliberează resursele asociate sesiunii.
  - Similar, dacă clientul nu primește un PINGRESP într-un interval de timp specificat după trimiterea unui PINGREQ, consideră că conexiunea s-a pierdut.

- Impactul asupra QoS:
  - Nivelurile de calitate a serviciului (QoS) influențează, de asemenea, mecanismul Keep Alive. De exemplu, dacă un mesaj cu QoS 1 sau 2 nu este confirmat de broker în intervalul Keep Alive, clientul poate retrimite mesajul.
  - Aceasta garantează că mesajele importante nu sunt pierdute din cauza problemelor de rețea sau a deconectărilor.

## Last Will

Mecanismul Last Will în MQTT este o modalitate de a notifica ceilalți clienți despre o deconectare neașteptată a unui client. Este o caracteristică esențială pentru construirea aplicațiilor IoT fiabile și tolerante la erori.

- Cum funcționează:
  - Declarația LW:
    - În timpul fazei de CONNECT, clientul specifică mesajul său Last Will. Acesta include topicul, mesajul, QoS-ul și flag-ul de păstrare.
    - Informațiile LW sunt trimise ca parte din pachetul CONNECT către broker.
  - Rolul brokerului:
    - Brokerul stochează informațiile LW și monitorizează conexiunea cu clientul.
    - Dacă clientul se deconectează neașteptat (de exemplu, din cauza unei defecțiuni a rețelei sau a unei erori la client), brokerul publică mesajul LW pe topicul specificat.
  - Notificare către subscriptori:
    - Mesajul LW este publicat pe topic la nivelul QoS specificat și cu flag-ul de păstrare, dacă este aplicabil.
    - Toți clienții abonați la topic vor primi mesajul LW, indicând faptul că clientul s-a deconectat neașteptat.

## Mecanismele QoS0, 1 și 2

Nivelurile de QoS definesc garanția livrării mesajelor între client și broker. Există trei nivele de QoS: 0, 1 și 2, fiecare oferind diferite nivele de asigurare pentru livrarea mesajelor. 

### QoS0: Cel mult o dată

- Descriere:
  - Mesajele sunt livrate cel mult o dată, fără confirmare. Acest nivel este cunoscut și sub denumirea de "fire and forget".

- Cum funcționează:
  - Clientul trimite un pachet PUBLISH către broker.
  - Brokerul nu confirmă primirea mesajului.
  - Dacă clientul sau brokerul este offline sau conexiunea este întreruptă, mesajul poate fi pierdut.

![MQTT QoS0](https://www.hivemq.com/sb-assets/f/243938/1024x360/41d4e98134/qos-levels_qos0.webp)

### QoS1: Cel puțin o dată

- Descriere:
  - Mesajele sunt livrate cel puțin o dată, garantând că mesajul ajunge la destinatarul dorit, dar poate fi livrat de mai multe ori.

- Cum funcționează:
  - Clientul trimite un pachet PUBLISH către broker și setează un identificator de pachet (Packet Identifier).
  - Brokerul trimite un pachet PUBACK pentru a confirma primirea mesajului.
  - Dacă clientul nu primește PUBACK, retrimite pachetul PUBLISH cu același identificator de pachet.
  - Acest proces continuă până când clientul primește PUBACK, asigurându-se că mesajul a fost livrat cel puțin o dată.

![MQTT QoS1](https://www.hivemq.com/sb-assets/f/243938/1024x360/529ab80be0/qos-levels_qos1.webp)

### QoS2: Exact o dată

- Descriere:
  - Mesajele sunt livrate exact o dată. Acest nivel oferă cea mai mare garanție de livrare a mesajului, asigurându-se că nu există duplicări și nici pierderi de mesaje.

- Cum funcționează:
  - Clientul trimite un pachet PUBLISH către broker cu un identificator de pachet.
  - Brokerul trimite un pachet PUBREC (Publish Received) pentru a confirma primirea mesajului.
  - Clientul trimite un pachet PUBREL (Publish Release) brokerului pentru a confirma că procesarea poate continua.
  - Brokerul trimite un pachet PUBCOMP (Publish Complete) clientului pentru a confirma finalizarea livrării.
  - Acest schimb de patru pași garantează că mesajul este livrat exact o dată.

![MQTT QoS2](https://www.hivemq.com/sb-assets/f/243938/1024x360/3b314a5496/qos-levels_qos2.webp)

## Interfata grafica

- Configurația Adresei Brokerului
    - Descriere
      - Utilizatorul va putea introduce adresa IP sau domeniul brokerului MQTT la care clientul se va conecta.
    - Funcționalitate:
        - Câmp pentru introducerea adresei brokerului.
        - Validarea adresei introduse pentru a asigura că este validă.
    - Exemplu de comportament al interfeței:
        - Câmpul de input pentru adresă va fi completabil de utilizator.
        - Dacă adresa este invalidă, va apărea un mesaj de eroare care explică utilizatorului cum să corecteze eroarea.

- Configurația ID-ului Clientului
    - Descriere:
      - Utilizatorul va putea configura un ID unic pentru clientul MQTT, care va fi utilizat pentru identificarea sa în rețea.
    - Funcționalitate:
        - Câmp pentru configurarea unui ID client care trebuie să fie unic pe broker.
        - Posibilitatea de a introduce un ID personalizat sau de a folosi o valoare implicită generată automat.
    - Exemplu de comportament al interfeței:
        - Câmpul pentru ID-ul clientului va fi vizibil în interfață.
        
- Configurația Mesajului LastWill
    - Descriere:
      - Utilizatorul va putea configura mesajul Last Will, inclusiv topicul, mesajul, QoS-ul și flag-ul de păstrare.
    - Funcționalitate:
        - Mesajul: Câmp de text în care utilizatorul va putea introduce mesajul care va fi trimis în caz de deconectare neașteptată.
        - QoS (Quality of Service): Dropdown pentru selectarea nivelului QoS (0, 1 sau 2). Fiecare opțiune va fi descrisă pentru a ajuta utilizatorul să aleagă corect:
            - QoS 0: Mesajul este livrat o singură dată.
            - QoS 1: Mesajul este livrat cel puțin o dată.
            - QoS 2: Mesajul este livrat exact o dată.
    - Exemplu de comportament al interfeței:
        - Câmpuri de input pentru topic și mesaj.
        - Dropdown pentru alegerea QoS.
        - Un checkbox pentru activarea/dezactivarea flag-ului de păstrare.
        - Oferirea unui mesaj de confirmare sau un prompt pentru a verifica dacă utilizatorul dorește să aplice schimbările.
   
## Diagrama de secvență

![Sequence Diagram](https://github.com/user-attachments/assets/eff995f4-6965-42d0-b48f-9d68c677395e)



## Detalii tehnice

Pentru a creea acest proiect ne-am folosit de modulele time, threading, tkinter, re, psutil, os, select și socket.

Am implementat următoarele mecanisme astfel:
  - Keep alive - Acesta nu a fost foarte greu de implementat. Doar prin folosirea modului time și prin niște ping-uri se poate implementa. Ce făceam noi era să măsurăm timpul în care teoretic ar fi să fie trimis un ping dacă nu se trimite niciun alt pachet. Această formulă este practic timpul actual, time.time() adică, adunat cu keep alive-ul pus pentru conexiune. Dacă această perioadă era depășită fără să se întâmple nimic, se dădea un ping. Dar dacă se trimitea vreun pachet acest temporizator era resetat.
  - QoS - Nivelurile de QoS au fost mai mult de muncă la ele. În principal pentru parsarea lor. Adică au fost verificate în primul rând că au fost făcute corect. Iar după dacă erau, se trimitea pachetul următor din acel handshake pentru QoS2. Dar aceasta este doar la trimitere, loc în care doar trebuia să parsăm PUBACK pentru QoS1 și PUBREC, să formăm și să trimitem PUBREL și să parsăm PUBCOMP pentru QoS2. Dar există posibilitatea și invers. Adică de exemplu când trimite altcineva pe același topic un PUBLISH. Brokerul ne trimite nouă acel PUBLISH, și prin urmare așteaptă PUBACK-ul la QoS1 și tot handshake-ul la QoS2. Altfel dacă nu se îndeplinește această condiție de a răspunde la mesaje cu răspunsurile necesare, conexiunea se va închide. Și din această cauză am făcut practic ceva legat de toate aceste semnale legate PUBLISH.
  - Împărțirea mesajelor - Aici mă refer la faptul că se mai întâmplă să vină unele pachete alipite sau incomplete. Și din această cauză am încercat să folosesc niște variabile intermediare pentru a împărți mesajele. Mai pe scurt aici era în principal vorba de acel remaining length, cu care se pot îmărți pachetele destul de ușor. Din testele mele această metodă în care verificam remaining length-ul nu a dat greș până acum. Dar cel mai probabil mai există cazuri în care mesajul nu iese complet corect.
  - Gestionarea thread-ului - Am ales să facem un thread separat pentru răspunsuri, și aici într-un fel a fost un pic de gândit pentru că trebuie ca thread-ul de răspunsuri să aștepte după un mesaj, pentru că dacă nu altfel programul s-ar fi închis. Acest lucru a fost posibil cu ajutorul Event din threading. Aici setam un eveniment de fiecare dată când făceam ceva să stea să aștepte până când îi răspunde thread-ul. Adică de exemplu dacă trimiteam un CONNECT main thread-ul trebuia să aștepte după CONNACK, și tot așa. Aceasta este cea mai bună variantă pe care am găsit-o.

Cele de sus au fost cam cele mai importante lucruri de făcut și cele mai complicate de implementat aș putea zice. În rest sunt handle-uri pentru toate mesajele de acknowlege și handshake-uri. 

Aici a fost foarte de ajutor documentația. Pentru a vedea exact ce trebuie verificat și cum. Adică dacă sunt ok proprietățile, lungimile, identificatoarele de pachete. Dacă sunt ok valorile rezervate să nu fie ceva schimbat etc. Și de asemenea documentația a fost de ajutor la formarea mesajelor pe care doream să le trimitem noi, și de asemenea pentru restul pachetelor care trebuiau create de noi cum ar fi CONNECT, SUBSCRIBE UNSUBSCRIBE și PUBLISH. PUBREL, PUBCOMP, PUBREC și PUBACK.

Cam atât în ceea ce privește clientul. Și la interfața grafică nu este nici aici foarte mult de explicat. O să repet că aici au ajutat modulele threading, tkinter, re, time și psutil. 

Threading a ajutat pentru a putea face o instanță a clientului separat și să folosim funcțiile oferite de el fără a bloca main thread-ul care era responsabil cu interfața grafică. Adică ar fi stat pe loc interfața fără acest modul. Mai este și re, care a fost folosit doar o dată pentru un regex legat de ip. time a fost folosit doar așa tot odată pentru a adăuga un lucru random la generarea unui client id. Și nu în cele din urmă psutil a fost de ajutor pentru aplicația demonstrativă. Care spunea să punem niște parametrii ai sistemului pe topicuri. Am ales să punem doar procentajul de folosire a procesoruluim al ram-ului și să publicăm temperatura unui nucleu.
