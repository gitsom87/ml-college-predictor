SELECT
    '2024' [Year],
	RoundNo,
	[Rank],
	a.instituteId,
	(SELECT replace(description, ',', ' ') FROM MD_Institute WHERE id=a.instituteId  AND boardId='135032421') College,	
	(SELECT case when a.allottedQuota='SO' THEN 'STATE QUOTA SEAT' when a.allottedQuota='PS' THEN 'MANAGEMENT QUOTA SEAT' 
	when a.allottedQuota='NR' THEN 'NRI QUOTA SEAT' when a.allottedQuota='IQ' THEN 'IN-SERVICE QUOTA SEAT' when a.allottedQuota='SD' THEN 'IN-SERVICE DNB QUOTA SEAT' END 
	FROM MD_Institute I WHERE id=a.instituteId  AND boardId='135032421') Quota,
	(SELECT replace(description, ',', ' ') FROM MD_Program WHERE id=a.programId  AND boardId='135032421') Course,
	UPPER(CASE WHEN SUBSTRING(a.allottedCat,1,2)='OP' THEN 'GN' ELSE SUBSTRING(a.allottedCat,1,2) END) Category,	
	CASE WHEN SUBSTRING(a.allottedCat,3,2)='PH' THEN '1' ELSE '0' END PH
	INTO UG_2024_Admission

FROM app_allotment a WHERE boardId='135032421'
AND a.roundNo=(select MAX(AA.roundNo) from App_Allotment AA WHERE AA.rollNo = a.rollNo AND boardId='135032421')
AND a.rollNo not in	(SELECT Rollno FROM App_Withdrawl WHERE boardId='135032421')
ORDER by a.[rank]

--drop table UG_2024_Admission


SELECT
    '2023' [Year],
	RoundNo,
	[Rank],
	a.instituteId,
	(SELECT replace(description, ',', ' ') FROM MD_Institute WHERE id=a.instituteId  AND boardId='135032321') College,	
	(SELECT case when a.allottedQuota='SO' THEN 'STATE QUOTA SEAT' when a.allottedQuota='PS' THEN 'MANAGEMENT QUOTA SEAT' 
	when a.allottedQuota='NR' THEN 'NRI QUOTA SEAT' when a.allottedQuota='IQ' THEN 'IN-SERVICE QUOTA SEAT' when a.allottedQuota='SD' THEN 'IN-SERVICE DNB QUOTA SEAT' END 
	FROM MD_Institute I WHERE id=a.instituteId  AND boardId='135032321') Quota,
	(SELECT replace(description, ',', ' ') FROM MD_Program WHERE id=a.programId  AND boardId='135032321') Course,
	UPPER(CASE WHEN SUBSTRING(a.allottedCat,1,2)='OP' THEN 'GN' ELSE SUBSTRING(a.allottedCat,1,2) END) Category,	
	CASE WHEN SUBSTRING(a.allottedCat,3,2)='PH' THEN '1' ELSE '0' END PH
	--INTO UG_2023_Admission

FROM app_allotment a WHERE boardId='135032321'
AND a.roundNo=(select MAX(AA.roundNo) from App_Allotment AA WHERE AA.rollNo = a.rollNo AND boardId='135032321')
AND a.rollNo not in	(SELECT Rollno FROM App_Withdrawl WHERE boardId='135032321')
ORDER by a.[rank]



--SELECT * INTO UG_2023_Admission FROM [WBMCC2023_Main]..UG_2023_Admission

SELECT
    '2025' [Year],
	RoundNo,
	[Rank],
	a.instituteId,
	(SELECT replace(description, ',', ' ') FROM MD_Institute WHERE id=a.instituteId  AND boardId='135032521') College,	
	(SELECT case when a.allottedQuota='SO' THEN 'STATE QUOTA SEAT' when a.allottedQuota='PS' THEN 'MANAGEMENT QUOTA SEAT' 
	when a.allottedQuota='NR' THEN 'NRI QUOTA SEAT' when a.allottedQuota='IQ' THEN 'IN-SERVICE QUOTA SEAT' when a.allottedQuota='SD' THEN 'IN-SERVICE DNB QUOTA SEAT' END 
	FROM MD_Institute I WHERE id=a.instituteId  AND boardId='135032521') Quota,
	(SELECT replace(description, ',', ' ') FROM MD_Program WHERE id=a.programId  AND boardId='135032521') Course,
	UPPER(CASE WHEN SUBSTRING(a.allottedCat,1,2)='OP' THEN 'GN' ELSE SUBSTRING(a.allottedCat,1,2) END) Category,	
	CASE WHEN SUBSTRING(a.allottedCat,3,2)='PH' THEN '1' ELSE '0' END PH
	--INTO UG_2025_Admission

FROM app_allotment a WHERE boardId='135032521'
AND a.roundNo=(select MAX(AA.roundNo) from App_Allotment AA WHERE AA.rollNo = a.rollNo AND boardId='135032521')
AND a.rollNo not in	(SELECT Rollno FROM App_Withdrawl WHERE boardId='135032521')
ORDER by a.[rank]

--TRUNCATE table ML_CollegeAdmissionRoundWise

--INSERT INTO ML_CollegeAdmissionRoundWise ([Year], RoundNo, [Rank], College, Quota, Course, Category, PH)
--SELECT [Year], RoundNo, [Rank], instituteId College, Quota, Course, Category, PH FROM RPT_YearWiseAdmissionData

select * from RPT_YearWiseAdmissionData
--drop table RPT_YearWiseAdmissionData

--delete FROM RPT_YearWiseAdmissionData WHERE roundno>4

Select * INTO RPT_YearWiseAdmissionData FROM 
(
SELECT * FROM UG_2023_Admission
UNION
SELECT * FROM UG_2024_Admission
UNION
SELECT * FROM UG_2025_Admission
)XX

select DISTINCT Quota FROM RPT_YearWiseAdmissionData

SELECT 
    [Year],
    RoundNo,
    [Rank],
    College,
    Quota,
    Course,
    Category,
    PH
FROM ML_CollegeAdmissionRoundWise