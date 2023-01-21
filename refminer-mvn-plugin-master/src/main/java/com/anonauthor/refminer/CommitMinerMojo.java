package com.anonauthor.refminer;

import java.io.File;
import java.util.List;
import java.util.stream.Collectors;

import org.apache.maven.plugin.AbstractMojo;
import org.apache.maven.plugin.MojoExecutionException;
import org.apache.maven.plugins.annotations.LifecyclePhase;
import org.apache.maven.plugins.annotations.Mojo;
import org.apache.maven.plugins.annotations.Parameter;
import org.apache.maven.plugins.annotations.ResolutionScope;
import org.apache.maven.project.MavenProject;
import org.eclipse.jgit.api.Git;
import org.eclipse.jgit.api.errors.GitAPIException;
import org.eclipse.jgit.api.errors.NoHeadException;
import org.eclipse.jgit.lib.Repository;
import org.eclipse.jgit.revwalk.RevCommit;
import org.refactoringminer.api.GitHistoryRefactoringMiner;
import org.refactoringminer.api.Refactoring;
import org.refactoringminer.api.RefactoringHandler;
import org.refactoringminer.rm1.GitHistoryRefactoringMinerImpl;

import gr.uom.java.xmi.diff.CodeRange;
import me.tongfei.progressbar.ProgressBar;

/*
 * taken from https://github.com/tsantalis/RefactoringMiner
 * 
 * @author preich
 *
 */

@Mojo(name = "prminer", requiresProject=false, defaultPhase = LifecyclePhase.NONE, requiresDependencyResolution = ResolutionScope.NONE)
public class CommitMinerMojo extends AbstractMojo {

	@Parameter(defaultValue = "${project}", readonly = true, required = false)
	MavenProject project;

	@Parameter( property = "gitURL", defaultValue = "")
	private String gitURL;

	@Parameter( property = "branch", defaultValue = "master")
	private String branch;
	
	
	@Parameter( property = "pullRequest", defaultValue = "")
	private String pullRequest;

	@Parameter( property = "refminerFilename", defaultValue = "refminer_commits.csv")
	private String refminerFilename = "";

	
	
	public static void main(String[] args) {
		new CommitMinerMojo().process(new File("."));
		
	}
	public static boolean isRootProject(MavenProject project) {
		MavenProject parent = project.getParent();
		return parent == null || parent.getFile() == null;
	}
	public void execute() throws MojoExecutionException {
		if (pullRequest.trim().isEmpty()) {
			process(null);
			return;
		}
		File dir = project.getBasedir();
		getLog().info("parent: " + project.getParentArtifact());
		
		if (!isRootProject(project)) {
			getLog().info("Ignoring " + dir + " because it has parent  " + project.getParent());
			return;
		}
		getLog().info("Processing " + dir);
		process(dir);
	}
	private void process(File dir) {
		try {

			GitHistoryRefactoringMiner miner = new GitHistoryRefactoringMinerImpl();

			CSVReporter mainReporter = new CSVReporter(refminerFilename, "commit", "refactoringType","refactoringName",
					"classesBefore","classesAfter","description");
			CSVReporter codeRangeReporter = new CSVReporter("refminer-coderange.csv", 
					"commit", "refactoringType","refactoringName","side",
					"codeElement","codeElementType","filePath","startLine","endLine",
					"startColumn","endColumn","description");

			final ProgressBar progressBar = new ProgressBar("commits",1);
			
			RefactoringHandler handler = new RefactoringHandler() {
				@Override
				public void handle(String commitId, List<Refactoring> refactorings) {
					for (Refactoring ref : refactorings) {
						processRefactoring(mainReporter, codeRangeReporter, commitId, ref);
					}
					progressBar.step();
				}
				@Override
				public void handleException(String commitId, Exception e) {
					getLog().error("Can't handle commit= " + commitId + " due to " + e.getMessage(), e);
					progressBar.step();
				}
			};
			getLog().info("gitURL: " + gitURL);
			if (gitURL != null && !gitURL.trim().isEmpty() && pullRequest != null && !pullRequest.trim().isEmpty() && Integer.valueOf(pullRequest) > 0) {
				int timeout=600;
				getLog().info("Use PRBasedMiner");
				miner = new GitHistoryRefactoringMinerImpl(org.refactoringminer.rm1.PRBasedMiner::new);

				miner.detectAtPullRequest(gitURL, Integer.valueOf(pullRequest), handler, timeout);
			} else {
				Git git = Git.open(dir);
				int commitCount = countCommits(git);
				progressBar.maxHint(commitCount);

				Repository repository = git.getRepository();

				miner.detectAll(repository, branch, handler);
			}

			progressBar.close();
			mainReporter.close();
			codeRangeReporter.close();
		} catch (Exception e) {
			getLog().error(e.getMessage(), e);
		}
	}
	private int countCommits(Git git) throws GitAPIException, NoHeadException {
		Iterable<RevCommit> commits = git.log().call();
		int count = 0;
		for (RevCommit commit : commits) {
			count++;
		}
		return count;
	}

	private void reportCodeRanges(CSVReporter reporter, String commitId, Refactoring ref, String side, List<CodeRange> codeRanges) {
		for (CodeRange range : codeRanges) {
			reporter.write(commitId, 
					ref.getRefactoringType(), 
					ref.getName(),
					side, 
					range.getCodeElement(),
					range.getCodeElementType(),
					range.getFilePath(),
					range.getStartLine(),
					range.getEndLine(),
					range.getStartColumn(),
					range.getEndColumn(),
					range.getDescription().replaceAll(";", ","));
		}
	}

	private void processRefactoring(CSVReporter mainReporter, CSVReporter codeRangeReporter, String commitData,
			Refactoring ref) {
		mainReporter.write(commitData, 
				ref.getRefactoringType(), 
				ref.getName(),
				ref.getInvolvedClassesBeforeRefactoring().stream().map(x->x.right).collect(Collectors.joining(",")),
				ref.getInvolvedClassesAfterRefactoring().stream().map(x->x.right).collect(Collectors.joining(",")),
				ref.toString().replaceAll(";", ",")
		);
		reportCodeRanges(codeRangeReporter, commitData, ref, "left", ref.leftSide());
		reportCodeRanges(codeRangeReporter, commitData, ref, "right", ref.rightSide());
	}
}
