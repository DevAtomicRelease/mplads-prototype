"""Reviewed source contract. New data must be profiled and this contract revised."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AS_OF = '2026-09-10'
VERSION = 'all-cohorts-2026-09-10-v2'
RECONCILIATION_TOLERANCE_PAISE = 100  # INR 1 screening tolerance; not a legal threshold.
COHORTS = ['Lok Sabha', 'Rajya_Sabha_retired', 'Rajya_Sabha_sitting']
COHORT_CODES = {'Lok Sabha':'LS', 'Rajya_Sabha_retired':'RSR', 'Rajya_Sabha_sitting':'RSS'}
KINDS = ['allocations','consents','recommended','sanctioned','completed','payments']
FILES = ['01_allocated_limit.csv','02_calamity_consent.csv','03_works_recommended.csv','04_works_sanctioned.csv','05_works_completed.csv','06_expenditure.csv']
CONTRACTS = [
 (543,'da79d9fecefcff66670dd4b656f1d624b1feee0f2c5560800fd5b77bb14a696b'),
 (12,'c653f3d0ebde00baabbd9fa375f830dc9c6755a5462e838ecbf514a2d35da373'),
 (107562,'f396f91ad15e0f63aae25e8171481e29007ad0c0632caed2cfd5b03c36e1c4a2'),
 (79881,'8b31c7f7c335458719d8db447d5b53f407f72f66d56f434aaa7cff3a14c476d5'),
 (34940,'458edd98ddc5b2c4b9b713aca5f81333661775758073d2827058db2621c96139'),
 (57349,'bba2f79a9c5390a7e3a3ccada22282d3b223ea8f365991bbdd5a5b7a5637086f'),
 (248,'af5ded2439679419b9bb8f646864ef778c291888b585c1bf53e9774e8d7c6c04'),
 (1,'ee931fe277645349f172ce6e344d6e94bcb937fbfbaa8f3c17a3d8151ee7b55a'),
 (26863,'92ce886b7d0a14c2518c6558c864a007a0f1f6919f5c07b9bdf3f825beb3721d'),
 (24524,'e7145deeb0b384c87921edf6b5f327047f9326976ccaed9eefa1630e47ae58e1'),
 (16282,'3f323198bdc3a7b3361cb8bfbb34f2c58ec45ccb7e3319713e3d839182965dd5'),
 (30994,'3b873f3dd0d6cd7b16254a5ffa1a3996a1103a4ec3a63d54ad63363fa298ccf3'),
 (232,'294dca8f3c616abd1a74b5e7e3ea812f1cfe8b6aecfdb656db37bcd22e48d94d'),
 (20,'000b52ae31c5068f112a7870bc75cfae3caebc7c27a061e0b37bdd21ca6667cc'),
 (25369,'1636c0a0e69d326d68b0eb6793ebb55bc225a7ed072146302508a61492ffdbbb'),
 (19750,'24566251fab1ac3fd05d90653d75a608e5e90e45598f62cd8dae9f7ec5016a92'),
 (10046,'f54d2b07ea706e727335fbe8882c9e92a0ce4a7a7d5c8a0abfe14705ac02975f'),
 (25349,'dd629ba934b8aa7535a54d38425ee12190ff0257429a5bf2cd1576ca2ff0e0f2'),
]
