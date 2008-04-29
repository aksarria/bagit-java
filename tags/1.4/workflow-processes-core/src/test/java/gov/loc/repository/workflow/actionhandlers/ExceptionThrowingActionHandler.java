package gov.loc.repository.workflow.actionhandlers;

public class ExceptionThrowingActionHandler extends BaseActionHandler {

	private static final long serialVersionUID = 1L;

	public ExceptionThrowingActionHandler(String actionHandlerConfig) {
		super(actionHandlerConfig);
	}
	
	@Override
	protected void execute() throws Exception {
		throw new Exception("Oops.  An exception occurred.");
	}

}
