This is a replication package for ICSE2023 paper Testability Refactoring in Pull Requests: Patterns and Trends.

It may be incomplete due to measures taken to anonymise the sources of data. For the screen-ready version of the paper, this replication package can be simplified and de-anonymised.




We take new_pullreq.csv from https://yuyue.github.io/res/paper/newPR_MSR2020.pdf, in particular from https://github.com/zhangxunhui/new_pullreq_msr2020 and further from https://zenodo.org/record/3922907/files/new_pullreq.csv?download=1 (2.2gb) as a source of PRs from which we derive a set of projects (together with projects from organization.csv and historical_projects.csv, which we abandon later).


fetcher.py is used to fetch a list of PRs together with modified files from github using GraphQL, paginated for the first 100 items.
The results are saved in cached folder (564mb).

refactoringminer is a patched version that takes content diff for the whole PR instead of processing every commit in the PR in order to skip merge/rebase commits as well as multiple commits being the part of the same refactoring. github-oauth.properties with github API key in it is necessary to run refactoringminer.
refminer-mvn-plugin is a maven plugin to run own patched version of refactoringminer.


miner.py used reviewed.csv to run refactoringminer. it produces testable_prs.csv and mined patterns are saved in .csv files in mined folder.
combine_sources.ipynb imports manually assessed PRs from google docs, the URLs have been nulled for anonymisation purposes. For the screen-ready 
icse2023-tables.ipynb generates tables/charts for the LaTeX template of the paper.