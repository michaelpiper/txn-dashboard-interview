GET /api/v1/transactions?
    _q={{%like%}}&
    start_date={{date_time}}&
    end_date={{date_time}}&
    status={{enum}}&
    type={{enum}}&
    trn_ref={{string}}&
    source={{enum}}&
    start={{int}}&
    limit={{int}}


|Parameters | Usages|
|---------------------|
| _q | find transaction using join from transactions + user + audio_logs+ transaction_flags|
| state_date | find transaction start date with date time e.g{YYYY/MM/DD HH:mm:ss} |
| state_date | find transaction end date with date time e.g{YYYY/MM/DD HH:mm:ss} |
| status| enums (QUEUED,IN_PROGRESS,PENDING_REVIEW,FAILED,COMPLETED) |
| type | enums(CREDIT, DEBIT)|
| trn_ref | filter by transaction reference |
| source | enum(api,mobile,web,desktop)|
| start | where transaction cursor should start from |
| limit | total number of transaction returned|