Catalog of refactoring patterns.

# List of refactoring patterns

## extract_method_for_override

This is the most common testability refactoring pattern. In this pattern methods are extracted in production code to be overridden in test code in a (anonymous) subclass or using Mockito framework. 
 
 Such methods are often declared as protected or package
private, to limit access to the methods from classes outside
 the package. Instead of subclassing the class under test, [Mockito.spy](https://javadoc.io/static/org.mockito/mockito-core/3.6.28/org/mockito/Mockito.html#spy-T-) technique is often used to generate a subclass using CGLIB.  This technique reduces amount of code necessary to override methods.

This pattern corresponds to Feathers’ [18] *Extract and Override Call*, *Subclass and Override Method* and *Extract and Override Getter*.

 Here are a few example of how this pattern is used:
 * in
 PR [pentaho-platform/1449](https://github.com/pentaho/pentaho-platform/pull/1449/files#diff-307cfab7ed4f8c91d6d74df4ff65b3ad7743ec0815e0f7985f492b2a0c9c9fa7R117), the method getXmlaExtra in class
 under test OlapServiceImpl has been extracted as protected, as
 shown on Figure 1. In the test code the method is overridden
 in an anonymous subclass to return a mock object.
* in PR [incubator-heron/536](https://github.com/apache/incubator-heron/pull/536/files) the method  LocalScheduler.startExecutorP rocess is overridden using 
Mockito.spy.
* in PR [knowm/XChange/20](https://github.com/knowm/XChange/pull/20/files#diff-e86870907f945dd9ee979cc2db491fea5c6cac1b487949c5dca8f1bb9affaf89R72)  this approach is used to isolate the class under test from its dependencies, to replace real HTTP calls with provided  HTTP responses. For this purpose, a named private subclass has been created.
* in PR[jchambers/pushy/43] (https://github.com/jchambers/pushy/pull/43/files#diff-d8d4d0360449e723dcea0539c99f4a9204ce7580708232190f21a5bfcfa3ffadR202) an exception in a thread is emulated programmatically from a unit-test. For this purpose an anonymous subclass has been created.

## extract_method_for_invocation

Sometimes developers extract a method in order to test it separately. Such methods can contain more complex logic, need to be isolated from UI/network/databases or are considered as more error-prone. 

Here are a few examples: 

*  In (https://github.com/CIRDLES/Topsoil/pull/162/files#diff-09a3faa4ad34d218bef2083e380a7ba75ab8d1a3cea32eacd5f176a6cb5aec5aR111)[Topsoil/162] writeSVGToOutputStream method has been extracted in order to isolate it from the surrounding UI code. 

* In (https://github.com/azkaban/azkaban/pull/1975/files#diff-878e7ea77023da333e20fe5a651af41f884d596abd7661ee4639f42b0ae5d2a7R71)[azkaban/1975], updateExecutions method has been  extracted into a different class and tested separately.

## widen_access_for_invocation

Attributes, methods in classes
and classes themselves can have different visibility in java:  private (visible to the same class), protected (visible to sub- classes), package-private (visible to members of the same package) and public (visible to all). It may be necessary to widen access to a method to invoke it from a unit-test in order to control or observe the state of the class under test. 

Here are a few examples:
 
* in (https://github.com/OryxProject/oryx/pull/164/files#diff-0b2092687a203ffad205378960c0a8539705350bd3332f1717476b8fb3dd8255R162)[oryx/164] private method calcSilhouetteCoefficient in class SilhouetteCoefficient is made package-private in order to invoke it from the paired unit-test and assert the calculation result. 
* in (https://github.com/ankidroid/Anki-Android/pull/5996/files#diff-9111bfc45842d27abc69f185215cc459a0773bfa881ea4525017beabc3a6d70bR752)[Anki-Android/5996] method typeAnsAnswerFilter is made package-protected in order to invoce it from a unit-test.
* in (https://github.com/jenkinsci/gitlab-plugin/pull/335/files#diff-373f3bc3bec91ae5d8397f8136a2c2d260a65617cd2f719537bc240e56119cbcR140)[gitlab-plugin/335] private class NoOpAction is made package-protected in order to assert the result of a method invocation.

## widen_access_for_override

Access to existing members of classes or classes themselves can be widened to override behavior of the class under test.

* in [OpenRefine/2839] access to method f indV alues is widened from protected to public in order to override it using Mockito in the test code.

## extract_class_for_invocation
A class under test can be decomposed into several classes
not only to reduce coupling as the end goal, but also to test it separately or to isolate it from the dependencies. A set of methods can be extracted into a separate independent class in order to test it outside the original class.

Here are a few examples:

*  in (https://github.com/jmxtrans/jmxtrans/pull/291/files#diff-55a66325a926dfab96b606daf8b70a2d6f74d11b744519b5c98d116186a39cf1R7)[jmxtrans/291] method CloudWatchWriter.convertToDouble extracted into class ObjectToDouble and tested in ObjectToDoubleTest,
which doesn’t need to know about dependencies of CloudW atchWriter.
* TODO: more examples

## extract_class_for_override

A piece of functionality in production code can be extracted into a separate class that can
be replaced with a different implementation provided in a unit-
test. This approach has been used in just 6.5% of testability
related refactorings and is relatively rare. 

Here are a few examples:

* In (https://github.com/dropwizard/metrics/pull/516/files?diff=split&w=1#diff-56e9e266d500baf4ba08a737a7933a572da8468fe29c206d5ca564f65987aa9dR642)[metrics/516] ObjectNameFactory interface is extracted and a mock implementation is used in a unit-test to override the behavior.
* TODO: more examples

## create_constructor

Especially in spring-based classes, an
[@Autowired]  constructor can be created to provide dependen-
[cies from] he client code, as opposed to private @Autowired
[attributes of the class that are harder to set directly from a unit-
test.


Here are a few examples:

*  In (https://github.com/dhis2/dhis2-core/pull/2892/files#diff-755ce64247e7039b26560990d290fe0bbd03bcc0ce6ed7cb9f65ba0ae7b73134R118)[dhis2-core/2892] SmsMessageSender constructor with
all attributes is added in order to initialize the class under
test from the relevant unit-test with mocked dependencies. 
* In (https://github.com/Alluxio/alluxio/pull/3818/files#diff-cc3b10453fa5d1d353abbbbc7d0deb9fa3eed89e499729fedf932d32a01acd43R64)[alluxio/3818] in addition to the default con-
structor that hard-wires dependencies, a secondary constructor
is created that allows to provide dependencies from a unit-test
so that mocked or custom implementations of dependencies
can be provided.

## add_constructor_param

An extended version of an existing constructor can be created that takes one or more additional parameters to pass dependencies.
In general, such constructors can be made package-private or protected and marked with @VisibleForTesting annotation to limit their usage to test-code only, 

Here are a few examples:

* In (https://github.com/openmrs/openmrs-contrib-android-client/pull/349files#diff-21e6dfb384292a19172eb526ff517140445ff7d3b3172b95eab5808b63db773fR48)[openmrs-contrib-android-client/349] a new constructor
 is created for PatientDashboardVitalsPresenter that accepts
 EncounterDAO and VisitApi dependencies to set attributes
 of the class. In the original constructor, the two attributes were initialised with a hard-wired implementation.
* In (https://github.com/apache/incubator-heron/pull/1889/files#diff-b2ccdca755c3f7791879246ff6b92e87c3ea784e57751ae3fd3f315cce5ebc39R98)[incubator-heron/1889] a @VisibleForTesting additional protected constructor has been created to instantiate an instance of WebSink from unit-tests.

## override_system_time

Sometimes developers need to override system time from unit-tests.
This pattern sometimes co-occurs with Add parameter to constructor described above, where an instance of Clock is provided in constructor.

Here are a few examples:

* In (https://github.com/azkaban/azkaban/pull/1975/files#diff-2d87c6fd865081ff5397628a7b3db37042e787e0762d9cb939811e202a60473fR175)[azkaban/1975], where system time is overridden in the unit test using joda-time DateTimeUtils.setCurrentMillisFixed method. 

## extract_attribute_for_assertion

In this rare pattern, a getter is extracted for an internal attribute in order to invoke it for assertion. 

Here are a few examples:

* in (https://github.com/apache/druid/pull/2878/files)[druid/2878]  a @VisibleForTesting package-private getter is used to read workersWithUnacknowledgedTask attribute in a unit-test. 
* TODO: more examples