SELECT Rank, Category, Quota, PH,
(select id from MD_Institute where description=c.College AND boardId='135032421')College
FROM ML_CollegeData c


select * from MD_Institute



select distinct allottedCat
from App_Allotment a where roundNo=1

select * from ML_CollegeData

--CREATE TABLE ML_CollegeData (
--    Id INT IDENTITY PRIMARY KEY,
--    Rank INT,
--    Category VARCHAR(10),
--    Quota VARCHAR(10),
--    College VARCHAR(200)
--);

--ALTER TABLE ML_CollegeData
--ADD PH CHAR(1);

--DROP TABLE ML_CollegeAdmissionRoundWise
CREATE TABLE ML_CollegeAdmissionRoundWise (
    Id INT IDENTITY PRIMARY KEY,
	[Year] INT,
	RoundNo INT,
    [Rank] INT,
	College VARCHAR(200),
	Quota VARCHAR(200),
	Course VARCHAR(200),
    Category VARCHAR(10),
	PH CHAR(1)
);




truncate table ML_CollegeData
INSERT INTO ML_CollegeData (Rank, Category, Quota, College, PH)
SELECT
    a.rank,

    -- Extract Category
    CASE
        WHEN a.allottedCat LIKE 'SC%' THEN 'SC'
        WHEN a.allottedCat LIKE 'ST%' THEN 'ST'
        WHEN a.allottedCat LIKE 'OP%' THEN 'UR'
        WHEN a.allottedCat LIKE 'EW%' THEN 'EWS'
WHEN a.allottedCat LIKE 'BA%' THEN 'OBC-A'
WHEN a.allottedCat LIKE 'BB%' THEN 'OBC-B'
WHEN a.allottedCat LIKE 'BC%' THEN 'OBC'
        ELSE a.allottedCat
    END AS Category,

    a.allottedQuota,

    i.description AS College,

    -- Extract PH
    CASE
        WHEN a.allottedCat LIKE '%PH' THEN 'Y'
        ELSE 'N'
    END AS PH

FROM App_Allotment a
JOIN MD_Institute i ON i.id = a.instituteId
WHERE a.roundNo = 1
AND a.rank IS NOT NULL;